// Embedding values as colour cells
function color(v, max) {
  const t = Math.max(-1, Math.min(1, v / (max || 1)));
  return t >= 0
    ? `color-mix(in oklab, var(--manila) ${Math.round(t * 100)}%, var(--paper-2))`
    : `color-mix(in oklab, var(--stamp) ${Math.round(-t * 100)}%, var(--paper-2))`;
}

export default function VectorStrip({ values = [], dim }) {
  if (!values.length) return null;
  const max = Math.max(...values.map(Math.abs));
  return (
    <figure className="vstrip">
      <div className="vstrip__cells" role="img" aria-label={`First ${values.length} of ${dim} dimensions`}>
        {values.map((v, i) => (
          <span key={i} className="vstrip__cell" style={{ background: color(v, max) }} title={`d${i}: ${v}`} />
        ))}
        <span className="vstrip__more">+{dim - values.length}</span>
      </div>
      <figcaption className="mono">
        [{values.slice(0, 6).map((v) => v.toFixed(3)).join(", ")}, …]
      </figcaption>
    </figure>
  );
}
