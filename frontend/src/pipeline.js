// Build run state from events
export function newRun(stepDefs, extra = {}) {
  return {
    status: "running",
    steps: stepDefs.map((s) => ({ ...s, status: "pending", data: {}, ms: null, progress: 0 })),
    error: null,
    ...extra,
  };
}

export function applyEvent(run, ev) {
  if (!run) return run;
  if (ev.type === "step") {
    let steps = run.steps;
    if (!steps.find((s) => s.id === ev.step)) {
      // conditional node (e.g. fallback)
      steps = steps.map((s) => (s.id === "generate" ? { ...s, id: ev.step, title: "Fallback" } : s));
    }
    steps = steps.map((s) =>
      s.id === ev.step
        ? { ...s, status: ev.status, data: { ...s.data, ...ev.data }, ms: ev.ms,
            progress: ev.status === "done" ? 1 : s.progress }
        : s
    );
    return { ...run, steps };
  }
  if (ev.type === "progress") {
    return { ...run, steps: run.steps.map((s) => (s.id === ev.step ? { ...s, progress: ev.value, data: { ...s.data, ...ev.data } } : s)) };
  }
  if (ev.type === "complete") return { ...run, status: "done", result: ev.result };
  if (ev.type === "error") return { ...run, status: "error", error: ev.message };
  return run;
}

export const fmt = (n) => (typeof n === "number" ? n.toLocaleString("en-IN") : n);
