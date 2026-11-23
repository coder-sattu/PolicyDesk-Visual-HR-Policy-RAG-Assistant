const BASE = import.meta.env.VITE_API_URL || "";

export async function getJSON(path, opts = {}) {
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const reduced = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Read NDJSON stream; pace step events
export async function streamEvents(path, opts, onEvent, { pace = 420 } = {}) {
  const res = await fetch(BASE + path, opts);
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line) continue;
      const ev = JSON.parse(line);
      onEvent(ev);
      // visible pacing
      if (ev.type === "step" && !reduced()) await sleep(ev.status === "running" ? pace : 120);
      if (ev.type === "progress" && !reduced()) await sleep(60);
    }
  }
}
