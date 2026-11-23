"""Ingestion pipeline as a LangGraph:
validate -> load -> clean -> chunk -> embed -> store
"""
import hashlib
import uuid
from pathlib import Path
from typing import Any, TypedDict

import numpy as np
from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.core.embeddings import get_embedder
from app.core.events import step
from app.core.vector_store import get_store
from app.ingestion.chunking import chunk_pages
from app.ingestion.cleaning import clean_pages
from app.ingestion.loaders import SUPPORTED, load_document


class IngestState(TypedDict, total=False):
    file_path: str
    filename: str
    doc_id: str
    file_hash: str
    pages: list[dict]
    cleaned: list[dict]
    chunks: list[dict]
    vectors: Any  # np.ndarray
    result: dict


def _preview(text: str, n: int = 220) -> str:
    return text[:n] + ("…" if len(text) > n else "")


def validate_node(state: IngestState) -> IngestState:
    with step("validate", "Validate file") as s:
        path = Path(state["file_path"])
        if path.suffix.lower() not in SUPPORTED:
            raise ValueError(f"Unsupported file type {path.suffix}. Use PDF, TXT or MD.")
        size = path.stat().st_size
        if size == 0:
            raise ValueError("File is empty")
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        store = get_store()
        existing = store.find_by_hash(file_hash)
        if existing:  # replace old copy
            store.delete_document(existing["doc_id"])
        s.emit("done", filename=state["filename"], size_kb=round(size / 1024, 1),
               sha256=file_hash[:16], replaced_existing=bool(existing))
        return {"file_hash": file_hash, "doc_id": uuid.uuid4().hex[:12]}


def load_node(state: IngestState) -> IngestState:
    with step("load", "Extract text") as s:
        pages = load_document(Path(state["file_path"]))
        total = sum(len(p["text"]) for p in pages)
        if total < 20:
            raise ValueError("No extractable text found (scanned PDF? OCR not enabled)")
        s.emit("done", pages=len(pages), characters=total,
               page_previews=[{"page": p["page"], "chars": len(p["text"]),
                               "preview": _preview(p["text"], 160)} for p in pages[:6]])
        return {"pages": pages}


def clean_node(state: IngestState) -> IngestState:
    with step("clean", "Clean text") as s:
        cleaned, stats = clean_pages(state["pages"])
        before = state["pages"][min(1, len(state["pages"]) - 1)]["text"]
        after = next((p["text"] for p in cleaned if p["page"] == min(2, len(state["pages"]))), "")
        s.emit("done", **stats, before_sample=_preview(before, 260), after_sample=_preview(after, 260))
        return {"cleaned": cleaned}


def chunk_node(state: IngestState) -> IngestState:
    cfg = get_settings()
    with step("chunk", "Split into chunks") as s:
        chunks = chunk_pages(state["cleaned"], cfg.chunk_size, cfg.chunk_overlap)
        if not chunks:
            raise ValueError("Chunking produced no chunks")
        sizes = [c["chars"] for c in chunks]
        s.emit("done", chunks=len(chunks), chunk_size=cfg.chunk_size, overlap=cfg.chunk_overlap,
               avg_chars=round(sum(sizes) / len(sizes)), min_chars=min(sizes), max_chars=max(sizes),
               splitter="RecursiveCharacterTextSplitter",
               samples=[{"index": c["chunk_index"], "page": c["page"], "section": c["section"],
                         "chars": c["chars"], "text": _preview(c["text"], 300)} for c in chunks[:8]])
        return {"chunks": chunks}


def embed_node(state: IngestState) -> IngestState:
    cfg = get_settings()
    with step("embed", "Create embeddings") as s:
        emb = get_embedder()
        texts = [c["text"] for c in state["chunks"]]
        out, bs = [], cfg.embedding_batch_size
        for i in range(0, len(texts), bs):
            out.append(emb.embed_documents(texts[i:i + bs]))
            done = min(i + bs, len(texts))
            s.progress(done / len(texts), embedded=done, total=len(texts))
        vectors = np.vstack(out)
        s.emit("done", model=emb.name, dim=emb.dim, vectors=len(vectors), batch_size=bs,
               normalized=True, vector_preview=[round(float(x), 4) for x in vectors[0][:24]])
        return {"vectors": vectors}


def store_node(state: IngestState) -> IngestState:
    with step("store", "Store in FAISS") as s:
        store = get_store()
        ids = store.add_document(state["doc_id"], state["filename"], state["file_hash"],
                                 len(state["pages"]), state["chunks"], state["vectors"])
        stats = store.stats()
        s.emit("done", doc_id=state["doc_id"], ids_range=[ids[0], ids[-1]], added=len(ids),
               **stats, persisted_to=str(store.index_path.name))
        return {"result": {"doc_id": state["doc_id"], "filename": state["filename"],
                           "chunks": len(ids), "pages": len(state["pages"]), **stats}}


def build_ingestion_graph():
    g = StateGraph(IngestState)
    for name, fn in [("validate", validate_node), ("load", load_node), ("clean", clean_node),
                     ("chunk", chunk_node), ("embed", embed_node), ("store", store_node)]:
        g.add_node(name, fn)
    g.add_edge(START, "validate")
    g.add_edge("validate", "load")
    g.add_edge("load", "clean")
    g.add_edge("clean", "chunk")
    g.add_edge("chunk", "embed")
    g.add_edge("embed", "store")
    g.add_edge("store", END)
    return g.compile()


ingestion_graph = build_ingestion_graph()

INGEST_STEPS = [
    {"id": "validate", "title": "Validate"}, {"id": "load", "title": "Load"},
    {"id": "clean", "title": "Clean"}, {"id": "chunk", "title": "Chunk"},
    {"id": "embed", "title": "Embed"}, {"id": "store", "title": "Store"},
]


def run_ingestion(file_path: Path, filename: str):
    """Yield UI events while the graph runs."""
    yield {"type": "start", "pipeline": "ingestion", "steps": INGEST_STEPS, "filename": filename}
    final = {}
    try:
        for mode, chunk in ingestion_graph.stream(
                {"file_path": str(file_path), "filename": filename},
                stream_mode=["custom", "values"]):
            if mode == "custom":
                yield chunk
            else:
                final = chunk
        yield {"type": "complete", "result": final.get("result", {})}
    except Exception as exc:  # surfaced to UI
        yield {"type": "error", "message": str(exc)}
