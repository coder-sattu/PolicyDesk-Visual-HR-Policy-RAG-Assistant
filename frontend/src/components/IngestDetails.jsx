import VectorStrip from "./VectorStrip.jsx";
import { fmt } from "../pipeline.js";

const EXPLAIN = {
  validate: "Checks the file type and size, and fingerprints it so the same file is never stored twice.",
  load: "Pulls the raw text out of every page. Layout mode keeps table rows on one line.",
  clean: "Removes repeated headers, footers and page numbers, and re-joins lines that were wrapped.",
  chunk: "Splits the text into overlapping pieces small enough to search precisely.",
  embed: "Turns every chunk into a vector of numbers that captures its meaning.",
  store: "Adds the vectors to the FAISS index on disk, with the chunk text kept alongside.",
};

function Stat({ label, value }) {
  return (
    <div className="stat">
      <dt>{label}</dt>
      <dd>{fmt(value)}</dd>
    </div>
  );
}

function Body({ step }) {
  const d = step.data;
  switch (step.id) {
    case "validate":
      return (
        <dl className="stats">
          <Stat label="File" value={d.filename} />
          <Stat label="Size" value={`${d.size_kb} KB`} />
          <Stat label="Fingerprint" value={<span className="mono">{d.sha256}</span>} />
          <Stat label="Older copy" value={d.replaced_existing ? "Replaced" : "None"} />
        </dl>
      );
    case "load":
      return (
        <>
          <dl className="stats">
            <Stat label="Pages" value={d.pages} />
            <Stat label="Characters" value={d.characters} />
          </dl>
          <div className="pages">
            {d.page_previews?.map((p) => (
              <article key={p.page} className="page">
                <header>
                  Page {p.page} <span>{fmt(p.chars)} chars</span>
                </header>
                <p>{p.preview}</p>
              </article>
            ))}
          </div>
        </>
      );
    case "clean":
      return (
        <>
          <dl className="stats">
            <Stat label="Before" value={`${fmt(d.chars_before)} chars`} />
            <Stat label="After" value={`${fmt(d.chars_after)} chars`} />
            <Stat label="Lines removed" value={d.removed_lines} />
            <Stat label="Table rows kept" value={d.table_rows_detected} />
          </dl>
          {d.removed_examples?.length > 0 && (
            <p className="removed">
              Removed:{" "}
              {d.removed_examples.map((r) => (
                <s key={r}>{r}</s>
              ))}
            </p>
          )}
          <div className="compare">
            <div>
              <h4>Raw text</h4>
              <pre>{d.before_sample}</pre>
            </div>
            <div>
              <h4>Cleaned</h4>
              <pre>{d.after_sample}</pre>
            </div>
          </div>
        </>
      );
    case "chunk":
      return (
        <>
          <dl className="stats">
            <Stat label="Chunks" value={d.chunks} />
            <Stat label="Size / overlap" value={`${d.chunk_size} / ${d.overlap}`} />
            <Stat label="Average" value={`${d.avg_chars} chars`} />
            <Stat label="Range" value={`${d.min_chars}–${d.max_chars}`} />
          </dl>
          <div className="chunkbar" aria-hidden>
            {Array.from({ length: d.chunks || 0 }).map((_, i) => (
              <span key={i} style={{ animationDelay: `${i * 35}ms` }} />
            ))}
          </div>
          <div className="chunks">
            {d.samples?.map((c) => (
              <article key={c.index} className="chunk">
                <header>
                  <b>#{c.index}</b> {c.section || "Front matter"} <span>page {c.page}, {c.chars} chars</span>
                </header>
                <p>{c.text}</p>
              </article>
            ))}
          </div>
        </>
      );
    case "embed":
      return (
        <>
          {step.status === "running" && (
            <div className="bar">
              <span style={{ width: `${Math.round(step.progress * 100)}%` }} />
            </div>
          )}
          <dl className="stats">
            <Stat label="Model" value={d.model} />
            <Stat label="Dimensions" value={d.dim} />
            <Stat label="Vectors" value={d.vectors ?? d.embedded} />
            <Stat label="Batch size" value={d.batch_size} />
          </dl>
          {d.vector_preview && (
            <>
              <h4>Chunk #0 as a vector</h4>
              <VectorStrip values={d.vector_preview} dim={d.dim} />
            </>
          )}
        </>
      );
    case "store":
      return (
        <>
          <dl className="stats">
            <Stat label="Added" value={d.added} />
            <Stat label="Total in index" value={d.vectors} />
            <Stat label="Documents" value={d.documents} />
            <Stat label="Index" value={<span className="mono">{d.index_type}</span>} />
          </dl>
          <div className="dots" aria-label={`${d.vectors} vectors in index`}>
            {Array.from({ length: Math.min(d.vectors || 0, 400) }).map((_, i) => (
              <span key={i} className={i >= (d.vectors - d.added) ? "new" : ""} />
            ))}
          </div>
          <p className="hint mono">
            ids {d.ids_range?.[0]}–{d.ids_range?.[1]}, doc {d.doc_id}, saved to {d.persisted_to}
          </p>
        </>
      );
    default:
      return null;
  }
}

export default function IngestDetails({ steps }) {
  const visible = steps.filter((s) => s.status !== "pending");
  return (
    <div className="log">
      {visible.map((s) => (
        <section key={s.id} className={`log__entry is-${s.status}`} id={`step-${s.id}`}>
          <header className="log__head">
            <h3>{s.title}</h3>
            <span className="log__time">{s.status === "done" ? `${s.ms} ms` : s.status}</span>
          </header>
          <p className="log__explain">{EXPLAIN[s.id]}</p>
          {s.status === "error" ? <p className="err">{s.data.error}</p> : <Body step={s} />}
        </section>
      ))}
    </div>
  );
}
