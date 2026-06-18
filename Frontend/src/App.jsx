import { useState, useEffect, useRef } from "react";

const API = "http://localhost:8000";

// ── tiny API helpers ──────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ── components ────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <span style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "var(--accent)",
            animation: `pulse 1.2s ${i * 0.2}s ease-in-out infinite`,
          }}
        />
      ))}
    </span>
  );
}

function SourceCard({ source, index }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={styles.sourceCard}>
      <button onClick={() => setOpen(!open)} style={styles.sourceToggle}>
        <span style={styles.sourceLabel}>Source {index + 1}</span>
        <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: "auto" }}>
          {open ? "▲ hide" : "▼ show"}
        </span>
      </button>
      {open && <p style={styles.sourceText}>{source.preview}</p>}
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div style={{ ...styles.msgRow, justifyContent: isUser ? "flex-end" : "flex-start" }}>
      {!isUser && (
        <div style={styles.avatar}>
          <span style={{ fontSize: 14 }}>⬡</span>
        </div>
      )}
      <div style={{ maxWidth: "72%" }}>
        <div style={{ ...styles.bubble, ...(isUser ? styles.userBubble : styles.aiBubble) }}>
          <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{msg.content}</p>
        </div>
        {msg.web_fallback && (
          <p style={styles.webBadge}>⚡ Web search used</p>
        )}
        {msg.sources && msg.sources.length > 0 && (
          <div style={{ marginTop: 6 }}>
            {msg.sources.map((s, i) => <SourceCard key={i} source={s} index={i} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function UploadPanel({ onDone }) {
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState(null); // null | "uploading" | "indexing" | "done" | Error
  const inputRef = useRef();

  async function handleUpload() {
    if (!files.length) return;
    setStatus("uploading");
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      await fetch(API + "/documents/upload", { method: "POST", body: fd });
      setStatus("indexing");
      await apiFetch("/documents/index", { method: "POST" });
      setStatus("done");
      setFiles([]);
      onDone?.();
    } catch (e) {
      setStatus(e);
    }
  }

  return (
    <div style={styles.uploadPanel}>
      <p style={styles.panelHeading}>Documents</p>
      <div
        style={styles.dropZone}
        onClick={() => inputRef.current.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          setFiles([...e.dataTransfer.files]);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          style={{ display: "none" }}
          onChange={(e) => setFiles([...e.target.files])}
        />
        {files.length
          ? files.map((f) => <p key={f.name} style={styles.fileName}>{f.name}</p>)
          : <p style={{ color: "var(--muted)", fontSize: 12, margin: 0 }}>Drop PDFs, TXT, or MD here</p>}
      </div>
      <button
        style={{ ...styles.btn, marginTop: 8, width: "100%", opacity: files.length ? 1 : 0.4 }}
        onClick={handleUpload}
        disabled={!files.length || typeof status === "string"}
      >
        {status === "uploading" ? "Uploading…" :
         status === "indexing" ? "Indexing…" :
         "Upload & Index"}
      </button>
      {status === "done" && <p style={{ color: "var(--green)", fontSize: 12, marginTop: 4 }}>✓ Documents indexed</p>}
      {status instanceof Error && <p style={{ color: "var(--red)", fontSize: 12, marginTop: 4 }}>{status.message}</p>}
    </div>
  );
}

// ── main app ──────────────────────────────────────────────────────────────

export default function App() {
  const [threads, setThreads] = useState([]);          // [{thread_id, title, message_count}]
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef();

  // scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // load thread list on mount
  useEffect(() => {
    loadThreads();
  }, []);

  async function loadThreads() {
    try {
      const data = await apiFetch("/threads");
      setThreads(data);
      // Auto-create a thread if none exist
      if (data.length === 0) await createThread();
    } catch (e) {
      // Server might not be up yet — that's okay
    }
  }

  async function createThread() {
    const t = await apiFetch("/threads/new", { method: "POST" });
    setActiveId(t.thread_id);
    setMessages([]);
    setThreads((prev) => [
      { thread_id: t.thread_id, title: "New Chat", message_count: 0 },
      ...prev,
    ]);
    return t.thread_id;
  }

  async function selectThread(tid) {
    setActiveId(tid);
    setError(null);
    try {
      const msgs = await apiFetch(`/threads/${tid}/messages`);
      setMessages(msgs);
    } catch (e) {
      setMessages([]);
    }
  }

  async function sendMessage() {
    if (!input.trim() || loading) return;
    const query = input.trim();
    setInput("");
    setError(null);

    let tid = activeId;
    if (!tid) tid = await createThread();

    // Optimistic user bubble
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);

    try {
      const res = await apiFetch("/chat", {
        method: "POST",
        body: JSON.stringify({ thread_id: tid, query }),
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          web_fallback: res.web_fallback,
          sources: res.sources,
        },
      ]);
      // Update thread title in sidebar
      setThreads((prev) =>
        prev.map((t) =>
          t.thread_id === tid
            ? { ...t, title: res.thread_title, message_count: t.message_count + 2 }
            : t
        )
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <>
      <style>{css}</style>
      <div style={styles.root}>
        {/* SIDEBAR */}
        <aside style={{ ...styles.sidebar, width: sidebarOpen ? 240 : 0, overflow: "hidden" }}>
          <div style={styles.sidebarInner}>
            <div style={styles.sidebarHeader}>
              <span style={styles.logo}>⬡ C-RAG</span>
              <button style={styles.iconBtn} onClick={() => setSidebarOpen(false)}>✕</button>
            </div>
            <button style={{ ...styles.btn, width: "100%", marginBottom: 12 }} onClick={createThread}>
              + New Chat
            </button>

            <div style={styles.threadList}>
              {threads.map((t) => (
                <button
                  key={t.thread_id}
                  style={{
                    ...styles.threadItem,
                    background: t.thread_id === activeId ? "var(--accent-dim)" : "transparent",
                    color: t.thread_id === activeId ? "var(--accent)" : "var(--text)",
                  }}
                  onClick={() => selectThread(t.thread_id)}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {t.title}
                  </span>
                </button>
              ))}
            </div>

            <div style={{ marginTop: "auto" }}>
              <UploadPanel onDone={loadThreads} />
            </div>
          </div>
        </aside>

        {/* MAIN */}
        <main style={styles.main}>
          {/* topbar */}
          <div style={styles.topbar}>
            {!sidebarOpen && (
              <button style={styles.iconBtn} onClick={() => setSidebarOpen(true)}>☰</button>
            )}
            <span style={styles.topbarTitle}>
              {threads.find((t) => t.thread_id === activeId)?.title ?? "C-RAG Research Assistant"}
            </span>
          </div>

          {/* messages */}
          <div style={styles.chatArea}>
            {messages.length === 0 && !loading && (
              <div style={styles.empty}>
                <p style={styles.emptyIcon}>⬡</p>
                <p style={styles.emptyTitle}>Ask anything about your documents</p>
                <p style={styles.emptyHint}>Upload PDFs in the sidebar, then start a question.</p>
              </div>
            )}
            {messages.map((msg, i) => <Message key={i} msg={msg} />)}
            {loading && (
              <div style={{ ...styles.msgRow, justifyContent: "flex-start" }}>
                <div style={styles.avatar}><span style={{ fontSize: 14 }}>⬡</span></div>
                <div style={{ ...styles.bubble, ...styles.aiBubble, padding: "10px 16px" }}>
                  <Spinner />
                </div>
              </div>
            )}
            {error && (
              <div style={styles.errorBanner}>⚠ {error}</div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* input */}
          <div style={styles.inputRow}>
            <textarea
              style={styles.textarea}
              placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
            />
            <button
              style={{ ...styles.sendBtn, opacity: input.trim() && !loading ? 1 : 0.4 }}
              onClick={sendMessage}
              disabled={!input.trim() || loading}
            >
              ↑
            </button>
          </div>
        </main>
      </div>
    </>
  );
}

// ── design tokens & styles ────────────────────────────────────────────────

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:        #0d0f14;
    --surface:   #161a22;
    --border:    #252b36;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --accent:    #6ee7b7;
    --accent-dim:#6ee7b71a;
    --user-bg:   #1e293b;
    --ai-bg:     #161a22;
    --green:     #6ee7b7;
    --red:       #f87171;
  }

  html, body, #root { height: 100%; background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; }

  @keyframes pulse {
    0%, 100% { opacity: .2; transform: scale(.8); }
    50%       { opacity: 1;  transform: scale(1.2); }
  }

  textarea { resize: none; font-family: inherit; }
  button { cursor: pointer; font-family: inherit; }
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
`;

const styles = {
  root: {
    display: "flex", height: "100vh", overflow: "hidden",
  },
  sidebar: {
    background: "var(--surface)", borderRight: "1px solid var(--border)",
    flexShrink: 0, transition: "width 0.2s ease",
  },
  sidebarInner: {
    width: 240, height: "100%", padding: 16,
    display: "flex", flexDirection: "column", gap: 0,
  },
  sidebarHeader: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    marginBottom: 16,
  },
  logo: { fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: "var(--accent)", fontSize: 15 },
  main: {
    flex: 1, display: "flex", flexDirection: "column", overflow: "hidden",
  },
  topbar: {
    padding: "12px 20px", borderBottom: "1px solid var(--border)",
    display: "flex", alignItems: "center", gap: 12, background: "var(--surface)",
    flexShrink: 0,
  },
  topbarTitle: { fontWeight: 500, fontSize: 14, color: "var(--text)" },
  chatArea: {
    flex: 1, overflowY: "auto", padding: "24px 20px",
    display: "flex", flexDirection: "column", gap: 20,
  },
  inputRow: {
    padding: "12px 16px", borderTop: "1px solid var(--border)",
    display: "flex", gap: 8, alignItems: "flex-end",
    background: "var(--surface)", flexShrink: 0,
  },
  textarea: {
    flex: 1, background: "var(--bg)", border: "1px solid var(--border)",
    borderRadius: 10, padding: "10px 14px", color: "var(--text)",
    fontSize: 14, lineHeight: 1.5, outline: "none",
    maxHeight: 120, overflowY: "auto",
  },
  sendBtn: {
    width: 40, height: 40, borderRadius: 10, border: "none",
    background: "var(--accent)", color: "#0d0f14", fontWeight: 700,
    fontSize: 18, display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0, transition: "opacity .15s",
  },
  msgRow: { display: "flex", gap: 10, alignItems: "flex-start" },
  avatar: {
    width: 32, height: 32, borderRadius: "50%",
    background: "var(--accent-dim)", border: "1px solid var(--accent)",
    display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0, color: "var(--accent)",
  },
  bubble: {
    borderRadius: 12, padding: "12px 16px", fontSize: 14,
    border: "1px solid var(--border)",
  },
  userBubble: { background: "var(--user-bg)", borderColor: "var(--border)" },
  aiBubble: { background: "var(--ai-bg)", borderColor: "var(--border)" },
  webBadge: { fontSize: 11, color: "var(--accent)", marginTop: 4, fontFamily: "'JetBrains Mono', monospace" },
  sourceCard: {
    marginTop: 6, borderRadius: 8, border: "1px solid var(--border)",
    overflow: "hidden", background: "var(--bg)",
  },
  sourceToggle: {
    width: "100%", background: "none", border: "none", color: "var(--text)",
    padding: "6px 10px", display: "flex", alignItems: "center", gap: 8,
    fontSize: 12, textAlign: "left",
  },
  sourceLabel: { fontFamily: "'JetBrains Mono', monospace", color: "var(--accent)", fontSize: 11 },
  sourceText: { padding: "8px 10px", fontSize: 12, color: "var(--muted)", lineHeight: 1.6 },
  btn: {
    background: "var(--accent-dim)", border: "1px solid var(--accent)",
    color: "var(--accent)", borderRadius: 8, padding: "8px 12px",
    fontSize: 13, fontWeight: 500, transition: "background .15s",
  },
  iconBtn: {
    background: "none", border: "none", color: "var(--muted)",
    fontSize: 16, padding: 4, lineHeight: 1,
  },
  threadList: { display: "flex", flexDirection: "column", gap: 2, flex: 1, overflowY: "auto" },
  threadItem: {
    width: "100%", background: "none", border: "none", borderRadius: 8,
    padding: "8px 10px", textAlign: "left", fontSize: 13,
    display: "flex", alignItems: "center", transition: "background .12s",
  },
  uploadPanel: { paddingTop: 12, borderTop: "1px solid var(--border)" },
  panelHeading: { fontSize: 11, fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 },
  dropZone: {
    border: "1px dashed var(--border)", borderRadius: 8, padding: "12px 8px",
    cursor: "pointer", textAlign: "center", minHeight: 52,
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 4,
  },
  fileName: { fontSize: 11, color: "var(--text)", margin: "2px 0", wordBreak: "break-all" },
  empty: {
    flex: 1, display: "flex", flexDirection: "column", alignItems: "center",
    justifyContent: "center", gap: 8, opacity: 0.5, marginTop: 80,
  },
  emptyIcon: { fontSize: 40, color: "var(--accent)" },
  emptyTitle: { fontSize: 16, fontWeight: 600 },
  emptyHint: { fontSize: 13, color: "var(--muted)" },
  errorBanner: {
    background: "#f871711a", border: "1px solid var(--red)",
    color: "var(--red)", borderRadius: 8, padding: "10px 14px", fontSize: 13,
  },
};