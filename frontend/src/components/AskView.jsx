import { useEffect, useRef, useState } from "react";
import TraceDetails from "./TraceDetails.jsx";
import Answer from "./Answer.jsx";

const SUGGESTED = [
  "How many days of sick leave do I get in a year?",
  "What is the notice period after confirmation?",
  "Can I work from home during probation?",
  "What is the hotel limit for a senior engineer on travel?",
  "How do I raise a POSH complaint?",
];

export default function AskView({ messages, busy, onSend, hasDocs }) {
  const [text, setText] = useState("");
  const [sel, setSel] = useState(null);
  const [cite, setCite] = useState(null);
  const endRef = useRef(null);

  const lastBot = [...messages.keys()].reverse().find((i) => messages[i].role === "assistant");
  const shown = sel ?? lastBot;
  const traced = shown != null ? messages[shown] : null;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  useEffect(() => {
    setSel(null);
  }, [messages.length]);

  const submit = (q) => {
    const v = (q ?? text).trim();
    if (!v || busy) return;
    setText("");
    setCite(null);
    onSend(v);
  };

  return (
    <div className="ask">
      <section className="chat" aria-label="Conversation">
        <div className="chat__scroll">
          {messages.length === 0 && (
            <div className="chat__intro">
              <h1>Ask the HR handbook</h1>
              <p>
                Answers come only from the documents in the index, with numbered sources you can check. The panel on
                the right shows how each answer was found.
              </p>
              {!hasDocs && <p className="err">The index is empty. Upload a policy PDF or use the sample first.</p>}
              <div className="suggest">
                {SUGGESTED.map((q) => (
                  <button key={q} type="button" className="chip" disabled={busy || !hasDocs} onClick={() => submit(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="msg msg--user">{m.content}</div>
            ) : (
              <div
                key={i}
                className={`msg msg--bot ${shown === i ? "is-traced" : ""}`}
                onClick={() => setSel(i)}
              >
                {m.content ? (
                  <Answer text={m.content} onCite={(n) => { setSel(i); setCite(n); }} />
                ) : m.run?.status === "error" ? null : (
                  <p className="typing" aria-label="Thinking"><span /><span /><span /></p>
                )}
                {m.run?.error && <p className="err">{m.run.error}</p>}
                {m.sources?.length > 0 && (
                  <p className="msg__sources">
                    Sources:{" "}
                    {m.sources.map((s) => (
                      <button key={s.n} type="button" className="srcchip" onClick={() => { setSel(i); setCite(s.n); }}>
                        [{s.n}] {s.section ? s.section.replace(/^\d+\.\s*/, "") : s.filename}, p.{s.page}
                      </button>
                    ))}
                  </p>
                )}
              </div>
            )
          )}
          <div ref={endRef} />
        </div>
        <form className="composer" onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <label htmlFor="q" className="sr-only">Your question</label>
          <textarea
            id="q"
            rows={1}
            value={text}
            placeholder={hasDocs ? "Ask about leave, notice period, travel, conduct…" : "Index a document first"}
            disabled={!hasDocs}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          />
          <button type="submit" className="btn btn--primary" disabled={busy || !text.trim() || !hasDocs}>
            {busy ? "Answering" : "Ask"}
          </button>
        </form>
      </section>

      <aside className="trace" aria-label="How this answer was found">
        <h2 className="trace__title">How this answer was found</h2>
        {!traced?.run ? (
          <p className="hint">Ask a question to see the retrieval graph run, step by step.</p>
        ) : (
          <>
            {traced.run.question && <p className="trace__q">“{traced.run.question}”</p>}
            <div className="trace__log">
              {traced.run.steps.map((s, i) => (
                <section key={s.id} className={`trace__step is-${s.status}`}>
                  <span className="trace__dot" aria-hidden>{s.status === "done" ? "✓" : s.status === "error" ? "!" : i + 1}</span>
                  <h3>
                    {s.title}
                    <span className="mono">{s.status === "done" && s.ms != null ? `${s.ms} ms` : s.status === "pending" ? "" : s.status}</span>
                  </h3>
                  {s.status !== "pending" && <TraceDetails step={s} all={traced.run.steps} highlight={cite} />}
                </section>
              ))}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
