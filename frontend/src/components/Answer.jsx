// Tiny safe markdown: lists, bold, [n] citations
function inline(text, onCite, key) {
  const parts = text.split(/(\*\*[^*]+\*\*|\[\d+\])/g);
  return parts.map((p, i) => {
    const k = `${key}-${i}`;
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={k}>{p.slice(2, -2)}</strong>;
    const m = p.match(/^\[(\d+)\]$/);
    if (m)
      return (
        <button key={k} type="button" className="cite" onClick={() => onCite?.(Number(m[1]))}
          aria-label={`Show source ${m[1]}`}>
          {m[1]}
        </button>
      );
    return p;
  });
}

export default function Answer({ text, onCite }) {
  const blocks = [];
  let list = null;
  text.split("\n").forEach((line, i) => {
    const li = line.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)$/);
    if (li) {
      if (!list) {
        list = [];
        blocks.push({ type: "ul", items: list, key: i });
      }
      list.push(li[1]);
    } else {
      list = null;
      if (line.trim()) blocks.push({ type: "p", text: line, key: i });
    }
  });
  return (
    <div className="answer">
      {blocks.map((b) =>
        b.type === "ul" ? (
          <ul key={b.key}>
            {b.items.map((it, j) => (
              <li key={j}>{inline(it, onCite, `${b.key}-${j}`)}</li>
            ))}
          </ul>
        ) : (
          <p key={b.key}>{inline(b.text, onCite, b.key)}</p>
        )
      )}
    </div>
  );
}
