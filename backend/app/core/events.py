"""Helpers to emit pipeline step events through LangGraph's custom stream."""
import time
from contextlib import contextmanager

from langgraph.config import get_stream_writer


class StepEmitter:
    def __init__(self, step: str, title: str):
        self.step, self.title = step, title
        self.writer = get_stream_writer()
        self.t0 = time.perf_counter()

    def emit(self, status: str, **data):
        self.writer({"type": "step", "step": self.step, "title": self.title, "status": status,
                     "ms": round((time.perf_counter() - self.t0) * 1000, 1), "data": data})

    def progress(self, value: float, **data):
        self.writer({"type": "progress", "step": self.step, "value": round(value, 3), "data": data})

    def raw(self, event: dict):
        self.writer(event)


@contextmanager
def step(name: str, title: str):
    em = StepEmitter(name, title)
    em.emit("running")
    try:
        yield em
    except Exception as exc:
        em.emit("error", error=str(exc))
        raise
