import VectorStrip from "./VectorStrip.jsx";

function Hits({ hits, threshold, keptIds, highlight }) {
  if (!hits?.length) return <p className="hint">The index returned nothing.</p>;
  return (
    <ul className="hits">
      {hits.map((h, i) => {
        const kept = keptIds ? keptIds.includes(h.id) : h.score >= threshold;
        return (
          <li key={h.id} className={`hit ${kept ? "" : "is-dropped"} ${highlight === i + 1 ? "is-hl" : ""}`}>
            <div className="hit__score">
              <span className="hit__bar">
                <span style={{ width: `${Math.max(4, h.score * 100)}%` }} />
                {threshold != null && <i style={{ left: `${threshold * 100}%` }} title={`threshold ${threshold}`} />}
              </span>
              <span className="mono">{h.score.toFixed(3)}</span>
            </div>
            <p className="hit__where">
              {h.section || "Front matter"}, page {h.page}
            </p>
            <details>
              <summary>{h.text.slice(0, 110)}…</summary>
              <p>{h.text}</p>
            </details>
          </li>
        );
      })}
    </ul>
  );
}

export default function TraceDetails({ step, all, highlight }) {
  const d = step.data;
  const grade = all.find((s) => s.id === "grade")?.data;
  if (step.status === "error") return <p className="err">{d.error}</p>;
  if (step.status === "running") return <p className="hint">Working…</p>;
  switch (step.id) {
    case "rewrite":
      return d.rewritten ? (
        <p>
          Your follow-up was rewritten so it can be searched on its own:
          <q>{d.standalone}</q>
        </p>
      ) : d.reason ? (
        <p>First question in this chat, so it is searched exactly as typed.</p>
      ) : (
        <p>Checked against the chat history. The question already makes sense on its own.</p>
      );
    case "embed_query":
      return (
        <>
          <p>
            Converted to a {d.dim}-dimension vector with <b>{d.model}</b>, the same model used for the chunks.
          </p>
          <VectorStrip values={d.vector_preview} dim={d.dim} />
        </>
      );
    case "search":
      return (
        <>
          <p>
            Compared against {d.searched_vectors} stored vectors by cosine similarity. Top {d.top_k}:
          </p>
          <Hits hits={d.hits} threshold={grade?.threshold} keptIds={grade?.kept_ids} highlight={highlight} />
        </>
      );
    case "grade":
      return (
        <p>
          Chunks scoring below <b>{d.threshold}</b> are dropped. Kept {d.kept}, dropped {d.dropped}, so the
          graph routes to <b>{d.route === "generate" ? "answer generation" : "the fallback reply"}</b>.
        </p>
      );
    case "generate":
      return (
        <dl className="stats stats--tight">
          <div className="stat"><dt>Model</dt><dd>{d.model}</dd></div>
          <div className="stat"><dt>Context chunks</dt><dd>{d.context_chunks}</dd></div>
          <div className="stat"><dt>First token</dt><dd>{d.first_token_ms} ms</dd></div>
          <div className="stat"><dt>Prompt size</dt><dd>{d.prompt_chars?.toLocaleString()} chars</dd></div>
        </dl>
      );
    case "fallback":
      return (
        <p>
          No chunk passed the relevance check ({d.reason}), so the assistant says so instead of guessing.
        </p>
      );
    default:
      return null;
  }
}
