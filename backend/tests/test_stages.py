"""Unit tests for each pipeline stage."""
import numpy as np

from app.core.config import get_settings
from app.ingestion.chunking import chunk_pages
from app.ingestion.cleaning import clean_pages
from app.ingestion.loaders import load_document


def test_stage_load(sample_pdf):
    pages = load_document(sample_pdf)
    assert len(pages) >= 4
    assert "Leave Policy" in " ".join(p["text"] for p in pages)


def test_stage_clean_removes_footer_keeps_table_values(sample_pdf):
    cleaned, stats = clean_pages(load_document(sample_pdf))
    text = "\n".join(p["text"] for p in cleaned)
    assert "HR Policy Handbook v3.0" not in text  # footer gone
    assert "Page 2" not in text
    assert "Earned / Privilege Leave | 18 | Up to 30 days" in text  # table row kept
    assert stats["removed_lines"] > 0 and stats["table_rows_detected"] > 0


def test_stage_chunk(sample_pdf):
    cfg = get_settings()
    cleaned, _ = clean_pages(load_document(sample_pdf))
    chunks = chunk_pages(cleaned, cfg.chunk_size, cfg.chunk_overlap)
    assert len(chunks) > 5
    assert all(c["chars"] <= cfg.chunk_size for c in chunks)
    assert any(c["section"] == "3. Leave Policy" for c in chunks)
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_stage_embed():
    from app.core.embeddings import get_embedder
    emb = get_embedder()
    vecs = emb.embed_documents(["sick leave policy", "travel allowance"])
    assert vecs.shape == (2, emb.dim) and vecs.dtype == np.float32
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-5)
    q = emb.embed_query("sick leave")
    assert float(vecs[0] @ q) > float(vecs[1] @ q)


def test_stage_vector_store_add_search_delete_persist(offline_env):
    from app.core.vector_store import FaissStore
    rng = np.random.default_rng(0)
    vecs = rng.normal(size=(3, 8)).astype("float32")
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    store = FaissStore(offline_env / "vs", 8)
    chunks = [{"chunk_index": i, "page": 1, "section": None, "text": f"t{i}", "chars": 2} for i in range(3)]
    store.add_document("d1", "a.pdf", "h1", 1, chunks, vecs)
    hits = store.search(vecs[1], 2)
    assert hits[0]["text"] == "t1" and abs(hits[0]["score"] - 1) < 1e-5
    reloaded = FaissStore(offline_env / "vs", 8)  # from disk
    assert reloaded.stats()["vectors"] == 3 and reloaded.find_by_hash("h1")
    assert reloaded.delete_document("d1") and reloaded.stats()["vectors"] == 0
    assert reloaded.search(vecs[0], 2) == []
