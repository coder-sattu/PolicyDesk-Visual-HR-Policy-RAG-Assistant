// Pipeline stations on a line
export default function Track({ steps, vertical = false, activeId, onSelect }) {
  return (
    <ol className={`track ${vertical ? "track--v" : ""}`}>
      {steps.map((s, i) => (
        <li key={s.id} className={`station is-${s.status} ${activeId === s.id ? "is-active" : ""}`}>
          <button
            type="button"
            className="station__btn"
            onClick={() => onSelect?.(s.id)}
            disabled={!onSelect || s.status === "pending"}
            aria-label={`${s.title}: ${s.status}`}
          >
            <span className="station__dot">
              {s.status === "done" ? "✓" : s.status === "error" ? "!" : i + 1}
            </span>
            <span className="station__label">
              <span className="station__title">{s.title}</span>
              <span className="station__meta">
                {s.status === "running" && s.progress > 0 && s.progress < 1
                  ? `${Math.round(s.progress * 100)}%`
                  : s.status === "running" ? "working" : s.ms != null ? `${s.ms} ms` : "waiting"}
              </span>
            </span>
          </button>
          {i < steps.length - 1 && (
            <span className="station__rail" aria-hidden>
              <span className="station__fill" />
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}
