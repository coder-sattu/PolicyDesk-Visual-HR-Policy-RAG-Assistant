"""LangGraph pipeline + API tests (offline)."""
import json

from fastapi.testclient import TestClient

from app.ingestion.graph import run_ingestion
from app.retrieval.graph import run_rag


def _done_steps(events):
    return [e["step"] for e in events if e["type"] == "step" and e["status"] == "done"]


def test_ingestion_graph_emits_every_step(sample_pdf):
    events = list(run_ingestion(sample_pdf, sample_pdf.name))
    assert events[0]["type"] == "start"
    assert _done_steps(events) == ["validate", "load", "clean", "chunk", "embed", "store"]
    assert any(e["type"] == "progress" and e["step"] == "embed" for e in events)
    assert events[-1]["type"] == "complete" and events[-1]["result"]["chunks"] > 5


def test_reingest_same_file_replaces(sample_pdf):
    first = list(run_ingestion(sample_pdf, sample_pdf.name))[-1]["result"]
    second = list(run_ingestion(sample_pdf, sample_pdf.name))
    val = next(e for e in second if e.get("step") == "validate" and e["status"] == "done")
    assert val["data"]["replaced_existing"] is True
    assert second[-1]["result"]["vectors"] == first["vectors"]  # no duplicates


def test_rag_graph_answers_with_sources(sample_pdf):
    list(run_ingestion(sample_pdf, sample_pdf.name))
    events = list(run_rag("How many days of sick leave do employees get?"))
    assert _done_steps(events) == ["rewrite", "embed_query", "search", "grade", "generate"]
    tokens = "".join(e["content"] for e in events if e["type"] == "token")
    final = events[-1]
    assert final["type"] == "complete" and final["answer"] == tokens.strip()
    assert final["sources"] and "Sick Leave" in " ".join(s["text"] for s in final["sources"])


def test_rag_graph_fallback_when_index_empty():
    events = list(run_rag("What is the notice period?"))
    assert "fallback" in _done_steps(events)
    assert "No documents" in events[-1]["answer"]


def test_rag_rewrite_with_history(sample_pdf):
    list(run_ingestion(sample_pdf, sample_pdf.name))
    hist = [{"role": "user", "content": "Tell me about leave"}, {"role": "assistant", "content": "..."}]
    events = list(run_rag("what about paternity?", hist))
    rw = next(e for e in events if e.get("step") == "rewrite" and e["status"] == "done")
    assert "standalone" in rw["data"]


def _ndjson(resp):
    return [json.loads(l) for l in resp.text.splitlines() if l.strip()]


def test_api_end_to_end(sample_pdf):
    from app.main import app
    with TestClient(app) as client:
        h = client.get("/api/health").json()
        assert h["status"] == "ok" and h["index"]["vectors"] == 0

        with open(sample_pdf, "rb") as f:
            r = client.post("/api/ingest", files={"file": ("handbook.pdf", f, "application/pdf")})
        assert r.status_code == 200 and r.headers["content-type"].startswith("application/x-ndjson")
        ev = _ndjson(r)
        assert ev[-1]["type"] == "complete"
        doc_id = ev[-1]["result"]["doc_id"]

        docs = client.get("/api/documents").json()["documents"]
        assert docs[0]["doc_id"] == doc_id
        assert len(client.get(f"/api/documents/{doc_id}/chunks").json()["chunks"]) > 5

        chat = _ndjson(client.post("/api/chat", json={"question": "What is the notice period after confirmation?"}))
        assert chat[-1]["type"] == "complete" and chat[-1]["sources"]

        assert client.post("/api/ingest", files={"file": ("x.exe", b"abc")}).status_code == 400
        assert client.post("/api/chat", json={"question": ""}).status_code == 422
        assert client.delete(f"/api/documents/{doc_id}").status_code == 200
        assert client.get("/api/health").json()["index"]["vectors"] == 0

        sample = _ndjson(client.post("/api/ingest/sample"))
        assert sample[-1]["type"] == "complete"
        assert client.delete("/api/documents").json()["index"]["vectors"] == 0


def test_api_reports_missing_groq_key(sample_pdf, monkeypatch):
    from app.core import config
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    config.get_settings.cache_clear()
    list(run_ingestion(sample_pdf, sample_pdf.name))
    events = list(run_rag("How many days of casual leave per year?"))
    assert any(e.get("step") == "generate" and e["status"] == "error" for e in events)
    assert events[-1]["type"] == "error" and "GROQ_API_KEY" in events[-1]["message"]
