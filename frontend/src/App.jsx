import { useCallback, useEffect, useState } from "react";
import { getJSON, streamEvents } from "./api.js";
import { applyEvent, newRun } from "./pipeline.js";
import Sidebar from "./components/Sidebar.jsx";
import IngestView from "./components/IngestView.jsx";
import AskView from "./components/AskView.jsx";
import ChunkDrawer from "./components/ChunkDrawer.jsx";

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthErr, setHealthErr] = useState(null);
  const [docs, setDocs] = useState([]);
  const [tab, setTab] = useState("ingest");
  const [ingestRun, setIngestRun] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [browse, setBrowse] = useState(null);
  const [toast, setToast] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [h, d] = await Promise.all([getJSON("/api/health"), getJSON("/api/documents")]);
      setHealth(h);
      setDocs(d.documents);
      setHealthErr(null);
    } catch {
      setHealthErr("Can't reach the backend. Start it with: uvicorn app.main:app --reload");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  // ingestion stream
  const ingest = async (path, opts, filename) => {
    setTab("ingest");
    setBusy(true);
    setIngestRun(null);
    let run = null;
    try {
      await streamEvents(path, opts, (ev) => {
        if (ev.type === "start") run = newRun(ev.steps, { filename: ev.filename });
        else run = applyEvent(run, ev);
        setIngestRun(run);
      });
    } catch (e) {
      setIngestRun({ ...(run || newRun([], { filename })), status: "error", error: e.message });
    } finally {
      setBusy(false);
      refresh();
    }
  };

  const upload = (file) => {
    const fd = new FormData();
    fd.append("file", file);
    ingest("/api/ingest", { method: "POST", body: fd }, file.name);
  };

  const sample = () => ingest("/api/ingest/sample", { method: "POST" }, "HR_Policy_Handbook.pdf");

  const remove = async (doc) => {
    if (!window.confirm(`Remove ${doc.filename} and its ${doc.chunks} vectors from the index?`)) return;
    await getJSON(`/api/documents/${doc.doc_id}`, { method: "DELETE" });
    setToast(`Removed ${doc.filename}`);
    refresh();
  };

  const reset = async () => {
    if (!window.confirm("Clear every document from the index?")) return;
    await getJSON("/api/documents", { method: "DELETE" });
    setToast("Index cleared");
    setIngestRun(null);
    refresh();
  };

  // chat stream
  const send = async (question) => {
    const history = messages
      .filter((m) => m.content && !m.run?.error)
      .slice(-6)
      .map(({ role, content }) => ({ role, content }));
    const idx = messages.length + 1;
    setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "", run: null }]);
    setBusy(true);
    const update = (fn) => setMessages((all) => all.map((m, i) => (i === idx ? fn(m) : m)));
    try {
      await streamEvents(
        "/api/chat",
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, history }) },
        (ev) => {
          if (ev.type === "start") update((m) => ({ ...m, run: newRun(ev.steps, { question }) }));
          else if (ev.type === "token") update((m) => ({ ...m, content: m.content + ev.content }));
          else if (ev.type === "complete") update((m) => ({ ...m, content: ev.answer, sources: ev.sources, run: applyEvent(m.run, ev) }));
          else update((m) => ({ ...m, run: applyEvent(m.run, ev) }));
        },
        { pace: 260 }
      );
    } catch (e) {
      update((m) => ({ ...m, run: { ...(m.run || newRun([])), status: "error", error: e.message } }));
    } finally {
      setBusy(false);
    }
  };

  const llmReady = health?.llm?.configured;

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <svg viewBox="0 0 32 32" aria-hidden><rect x="5" y="3" width="22" height="26" rx="3" fill="var(--manila)" /><path d="M10 11h12M10 16h12M10 21h7" stroke="var(--ink)" strokeWidth="2.4" strokeLinecap="round" /></svg>
          <span>Policy Desk</span>
        </div>
        <nav className="tabs" aria-label="Views">
          <button type="button" className={tab === "ingest" ? "is-on" : ""} onClick={() => setTab("ingest")}>Ingest</button>
          <button type="button" className={tab === "ask" ? "is-on" : ""} onClick={() => setTab("ask")}>Ask</button>
        </nav>
        <dl className="status">
          <div><dt>LLM</dt><dd className={llmReady ? "" : "warn"}>{health ? (health.llm.provider === "mock" ? "mock (offline)" : health.llm.model) : "…"}{health && !llmReady ? ", key missing" : ""}</dd></div>
          <div><dt>Embeddings</dt><dd>{health ? `${health.embeddings.model} (${health.embeddings.dim}d)` : "…"}</dd></div>
          <div><dt>Vectors</dt><dd>{health?.index?.vectors ?? "…"}</dd></div>
        </dl>
      </header>
      {healthErr && <p className="err err--banner err--top">{healthErr}</p>}

      <div className="body">
        <Sidebar docs={docs} busy={busy} onUpload={upload} onSample={sample} onDelete={remove}
          onBrowse={setBrowse} onReset={reset} />
        <main className="main">
          {tab === "ingest" ? (
            <IngestView run={ingestRun} onAsk={() => setTab("ask")} />
          ) : (
            <AskView messages={messages} busy={busy} onSend={send} hasDocs={docs.length > 0} />
          )}
        </main>
      </div>

      {browse && <ChunkDrawer doc={browse} onClose={() => setBrowse(null)} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}
