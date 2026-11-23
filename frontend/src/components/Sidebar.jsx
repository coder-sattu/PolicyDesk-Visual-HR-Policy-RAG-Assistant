import { useRef, useState } from "react";

export default function Sidebar({ docs, busy, onUpload, onSample, onDelete, onBrowse, onReset }) {
  const input = useRef(null);
  const [drag, setDrag] = useState(false);

  const pick = (files) => {
    const f = files?.[0];
    if (f) onUpload(f);
  };

  return (
    <aside className="side">
      <h2 className="side__title">Policy documents</h2>
      <div
        className={`drop ${drag ? "is-drag" : ""} ${busy ? "is-busy" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); if (!busy) pick(e.dataTransfer.files); }}
      >
        <svg viewBox="0 0 40 48" className="drop__icon" aria-hidden>
          <path d="M4 4h22l10 10v30H4z" fill="var(--manila)" />
          <path d="M26 4v10h10" fill="none" stroke="var(--ink)" strokeWidth="2" />
          <path d="M11 24h18M11 31h18M11 38h11" stroke="var(--ink)" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        <p>Drop a policy PDF here</p>
        <button type="button" className="btn btn--primary" disabled={busy} onClick={() => input.current?.click()}>
          Choose file
        </button>
        <input ref={input} type="file" accept=".pdf,.txt,.md" hidden
          onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
        <small>PDF, TXT or MD, up to 20 MB</small>
      </div>
      <button type="button" className="btn btn--ghost btn--block" disabled={busy} onClick={onSample}>
        Use the sample HR handbook
      </button>
      <a className="side__link" href="/api/sample" download>Download sample PDF</a>

      <h2 className="side__title">In the index</h2>
      {docs.length === 0 ? (
        <p className="side__empty">Nothing indexed yet. Upload a PDF or use the sample to start.</p>
      ) : (
        <ul className="docs">
          {docs.map((d) => (
            <li key={d.doc_id} className="doc">
              <div className="doc__name" title={d.filename}>{d.filename}</div>
              <div className="doc__meta">{d.pages} pages, {d.chunks} chunks</div>
              <div className="doc__actions">
                <button type="button" className="link" onClick={() => onBrowse(d)}>View chunks</button>
                <button type="button" className="link link--danger" disabled={busy} onClick={() => onDelete(d)}>
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {docs.length > 0 && (
        <button type="button" className="link link--danger side__reset" disabled={busy} onClick={onReset}>
          Clear the whole index
        </button>
      )}
    </aside>
  );
}
