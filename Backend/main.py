from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, sqlite3, json
from pathlib import Path
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="CRAG Research Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

THREADS_DB = "checkpoints.db"

def _conn():
    c = sqlite3.connect(THREADS_DB)
    c.row_factory = sqlite3.Row
    return c

def _init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_threads (
                thread_id TEXT PRIMARY KEY,
                title     TEXT NOT NULL DEFAULT 'New Chat',
                messages  TEXT NOT NULL DEFAULT '[]'
            )
        """)
        c.commit()

_init_db()


def _get_thread(tid):
    with _conn() as c:
        row = c.execute("SELECT * FROM chat_threads WHERE thread_id=?", (tid,)).fetchone()
    if row is None:
        return None
    return {"thread_id": row["thread_id"], "title": row["title"],
            "messages": json.loads(row["messages"])}

def _create_thread(tid, title="New Chat"):
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO chat_threads (thread_id, title, messages) VALUES (?,?,?)",
            (tid, title, "[]"),
        )
        c.commit()

def _append_messages(tid, new_msgs):
    with _conn() as c:
        row = c.execute("SELECT messages FROM chat_threads WHERE thread_id=?", (tid,)).fetchone()
        existing = json.loads(row["messages"]) if row else []
        c.execute("UPDATE chat_threads SET messages=? WHERE thread_id=?",
                  (json.dumps(existing + new_msgs), tid))
        c.commit()

def _set_title(tid, title):
    with _conn() as c:
        c.execute("UPDATE chat_threads SET title=? WHERE thread_id=?", (title, tid))
        c.commit()

def _all_threads():
    with _conn() as c:
        rows = c.execute(
            "SELECT thread_id, title, messages FROM chat_threads ORDER BY rowid DESC"
        ).fetchall()
    return [
        {"thread_id": r["thread_id"], "title": r["title"],
         "message_count": len(json.loads(r["messages"]))}
        for r in rows
    ]


# Request / Response models 

class ChatRequest(BaseModel):
    thread_id: str
    query: str

class ChatResponse(BaseModel):
    answer: str
    web_fallback: bool
    sources: list[dict]
    thread_title: str

class ThreadMeta(BaseModel):
    thread_id: str
    title: str
    message_count: int

class NewThreadResponse(BaseModel):
    thread_id: str


# Thread management 

@app.post("/threads/new", response_model=NewThreadResponse)
def new_thread():
    tid = str(uuid.uuid4())
    _create_thread(tid)
    return {"thread_id": tid}


@app.get("/threads", response_model=list[ThreadMeta])
def list_threads():
    return _all_threads()


@app.get("/threads/{thread_id}/messages")
def get_messages(thread_id: str):
    t = _get_thread(thread_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return t["messages"]


# Chat 

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if _get_thread(req.thread_id) is None:
        _create_thread(req.thread_id)

    from graph import app as langgraph_app

    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        result = langgraph_app.invoke(
            {"messages": [HumanMessage(content=req.query)], "retry_count": 0},
            config=config,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=400,
            detail="No vector database found. Upload documents and index them first.",
        )

    answer: str = result.get("generation", "")
    web_fallback: bool = bool(result.get("web_fallback", False))

    sources = []
    for doc in result.get("documents", []):
        preview = doc.page_content[:300]
        if len(doc.page_content) > 300:
            preview += "..."
        sources.append({"preview": preview})

    _append_messages(req.thread_id, [
        {"role": "user", "content": req.query},
        {"role": "assistant", "content": answer,
         "web_fallback": web_fallback, "sources": sources},
    ])

    t = _get_thread(req.thread_id)
    if len(t["messages"]) == 2:
        title = req.query[:30] + ("..." if len(req.query) > 30 else "")
        _set_title(req.thread_id, title)
    else:
        title = t["title"]

    return ChatResponse(
        answer=answer,
        web_fallback=web_fallback,
        sources=sources,
        thread_title=title,
    )


# Document ingestion

@app.post("/documents/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    saved = []
    for f in files:
        if not f.filename.endswith((".pdf", ".txt", ".md")):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.filename}")
        dest = docs_dir / f.filename
        dest.write_bytes(await f.read())
        saved.append(f.filename)
    return {"uploaded": saved}


@app.post("/documents/index")
def index_documents():
    from ingest import load_documents, split_documents, build_vectorstore, DOCS_DIR, CHROMA_DIR
    try:
        docs = load_documents(DOCS_DIR)
        chunks = split_documents(docs)
        build_vectorstore(chunks, CHROMA_DIR)
        return {"status": "ok", "chunks_indexed": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))