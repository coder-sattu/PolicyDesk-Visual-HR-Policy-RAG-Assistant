import Track from "./Track.jsx";
import IngestDetails from "./IngestDetails.jsx";

const IDLE_STEPS = ["Validate", "Load", "Clean", "Chunk", "Embed", "Store"].map((t) => ({
  id: t.toLowerCase(), title: t, status: "pending", ms: null, progress: 0, data: {},
}));

export default function IngestView({ run, onAsk }) {
  const scrollTo = (id) => document.getElementById(`step-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });

  if (!run) {
    return (
      <div className="view">
        <header className="view__head">
          <h1>From PDF to searchable knowledge</h1>
          <p>
            Upload a policy document and watch it move through six stations. Each one shows exactly what it did to
            your text, so you can see how retrieval-augmented generation works under the hood.
          </p>
        </header>
        <Track steps={IDLE_STEPS} />
        <div className="empty">
          <p>No document is being processed. Choose a PDF on the left, or use the sample HR handbook.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="view">
      <header className="view__head">
        <h1>Ingesting {run.filename}</h1>
        <p>
          {run.status === "running" && "The ingestion graph is running. Select a finished station to jump to its output."}
          {run.status === "done" && `Done. ${run.result?.chunks} chunks are now searchable, alongside ${run.result?.vectors} vectors in total.`}
          {run.status === "error" && "Ingestion stopped. Fix the problem below and upload again."}
        </p>
      </header>
      <Track steps={run.steps} onSelect={scrollTo} />
      {run.error && <p className="err err--banner">{run.error}</p>}
      <IngestDetails steps={run.steps} />
      {run.status === "done" && (
        <div className="finish">
          <p>The handbook is indexed. Ask it something an employee would ask HR.</p>
          <button type="button" className="btn btn--primary" onClick={onAsk}>Ask a question</button>
        </div>
      )}
    </div>
  );
}
