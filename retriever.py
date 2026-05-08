from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from pathlib import Path

CHROMA_DIR = "chroma_db"
TOP_K = 6
SCORE_THRESHOLD = 0.4

def get_retriever()-> VectorStoreRetriever:
    if not Path(CHROMA_DIR).exists():
        raise FileNotFoundError(
            f"'{CHROMA_DIR}/' not found. Run `python ingest.py` first."
        )
    embeddings = HuggingFaceEmbeddings(model="sentence-transformers/all-MiniLM-L6-v2")

    vectorstore= Chroma(
        persist_directory= CHROMA_DIR,
        embedding_function= embeddings,
    )
    retriever = vectorstore.as_retriever(
        search_type = "similarity",
        search_kwargs = {"k": TOP_K,},
    )
    return retriever
retriever = get_retriever()
