import { useEffect, useState } from "react";
import { getJSON } from "../api.js";

export default function ChunkDrawer({ doc, onClose }) {
  const [chunks, setChunks] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    getJSON(`/api/documents/${doc.doc_id}/chunks`).then((r) => setChunks(r.chunks)).catch((e) => setErr(e.message));
  }, [doc.doc_id]);

  useEffect(() => {
    const esc = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);

  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label={`Chunks of ${doc.filename}`}>
      <div className="drawer__scrim" onClick={onClose} />
      <div className="drawer__panel">
        <header className="drawer__head">
          <div>
            <h2>{doc.filename}</h2>
            <p>{doc.chunks} chunks stored in FAISS</p>
          </div>
          <button type="button" className="btn btn--ghost" onClick={onClose} autoFocus>Close</button>
        </header>
        {err && <p className="err">{err}</p>}
        {!chunks && !err && <p className="hint">Loading chunks…</p>}
        <div className="chunks chunks--list">
          {chunks?.map((c) => (
            <article key={c.chunk_index} className="chunk">
              <header>
                <b>#{c.chunk_index}</b> {c.section || "Front matter"} <span>page {c.page}, {c.chars} chars</span>
              </header>
              <p>{c.text}</p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
