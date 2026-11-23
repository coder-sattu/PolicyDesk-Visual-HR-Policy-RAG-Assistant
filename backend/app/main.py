import json
import logging
import re
import shutil
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.embeddings import get_embedder
from app.core.vector_store import get_store
from app.ingestion.graph import run_ingestion
from app.ingestion.loaders import SUPPORTED
from app.retrieval.graph import run_rag

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hr-rag")


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings().upload_dir.mkdir(parents=True, exist_ok=True)
    log.info("Loading embedder (%s)…", get_settings().embedding_provider)
    log.info("Ready: %s", get_store().stats())  # loads embedder + index
    yield


app = FastAPI(title=get_settings().app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_list, allow_methods=["*"],
                   allow_headers=["*"])


def ndjson(events):
    for e in events:
        yield json.dumps(e, default=str) + "\n"


def stream(events):
    return StreamingResponse(ndjson(events), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    history: list[ChatMessage] = []


@app.get("/api/health")
def health():
    emb = get_embedder()
    return {
        "status": "ok", "environment": get_settings().environment,
        "llm": {"provider": get_settings().llm_provider, "model": get_settings().groq_model,
                "fast_model": get_settings().groq_fast_model,
                "configured": get_settings().llm_provider == "mock" or bool(get_settings().groq_api_key)},
        "embeddings": {"provider": get_settings().embedding_provider, "model": emb.name, "dim": emb.dim},
        "chunking": {"size": get_settings().chunk_size, "overlap": get_settings().chunk_overlap},
        "retrieval": {"top_k": get_settings().top_k, "threshold": get_settings().score_threshold},
        "index": get_store().stats(),
    }


@app.get("/api/documents")
def list_documents():
    return {"documents": get_store().list_documents(), "index": get_store().stats()}


@app.get("/api/documents/{doc_id}/chunks")
def document_chunks(doc_id: str):
    chunks = get_store().get_chunks(doc_id)
    if not chunks:
        raise HTTPException(404, "Document not found")
    return {"doc_id": doc_id, "chunks": chunks}


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    if not get_store().delete_document(doc_id):
        raise HTTPException(404, "Document not found")
    return {"deleted": doc_id, "index": get_store().stats()}


@app.delete("/api/documents")
def reset_index():
    get_store().reset()
    return {"reset": True, "index": get_store().stats()}


@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...)):
    name = re.sub(r"[^\w.\- ]", "_", file.filename or "upload")
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in SUPPORTED:
        raise HTTPException(400, f"Only {', '.join(sorted(SUPPORTED))} files are supported")
    dest = get_settings().upload_dir / f"{uuid.uuid4().hex[:8]}_{name}"
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > get_settings().max_upload_mb * 1024 * 1024:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File larger than {get_settings().max_upload_mb} MB")
            out.write(chunk)
    log.info("Ingesting %s (%d bytes)", name, size)
    return stream(run_ingestion(dest, name))


@app.post("/api/ingest/sample")
def ingest_sample():
    if not get_settings().sample_doc.exists():
        raise HTTPException(404, "Sample document missing")
    dest = get_settings().upload_dir / get_settings().sample_doc.name
    shutil.copy(get_settings().sample_doc, dest)
    return stream(run_ingestion(dest, get_settings().sample_doc.name))


@app.get("/api/sample")
def download_sample():
    return FileResponse(get_settings().sample_doc, filename=get_settings().sample_doc.name)


@app.post("/api/chat")
def chat(req: ChatRequest):
    log.info("Question: %s", req.question)
    return stream(run_rag(req.question, [m.model_dump() for m in req.history]))


# prod: serve built UI
if get_settings().frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=get_settings().frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = get_settings().frontend_dist / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(get_settings().frontend_dist / "index.html")
