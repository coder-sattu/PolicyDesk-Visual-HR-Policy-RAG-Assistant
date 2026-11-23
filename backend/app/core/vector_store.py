"""FAISS vector store with a JSON docstore, persisted to disk."""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np


class FaissStore:
    def __init__(self, directory: Path, dim: int):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.faiss"
        self.meta_path = self.dir / "docstore.json"
        self.dim = dim
        self._lock = threading.RLock()
        self._load()

    # persistence
    def _new_index(self):
        # cosine via inner product
        return faiss.IndexIDMap2(faiss.IndexFlatIP(self.dim))

    def _load(self):
        if self.index_path.exists() and self.meta_path.exists():
            index = faiss.read_index(str(self.index_path))
            meta = json.loads(self.meta_path.read_text())
            if index.d == self.dim:
                self.index = index
                self.chunks: dict[str, dict] = meta["chunks"]
                self.documents: dict[str, dict] = meta["documents"]
                self.next_id: int = meta["next_id"]
                return
        # fresh or dim mismatch
        self.index = self._new_index()
        self.chunks, self.documents, self.next_id = {}, {}, 0

    def _save(self):
        faiss.write_index(self.index, str(self.index_path))
        tmp = self.meta_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"chunks": self.chunks, "documents": self.documents,
                                   "next_id": self.next_id}))
        tmp.replace(self.meta_path)

    # writes
    def add_document(self, doc_id: str, filename: str, file_hash: str, pages: int,
                     chunks: list[dict], vectors: np.ndarray) -> list[int]:
        assert vectors.shape == (len(chunks), self.dim), "vector shape mismatch"
        with self._lock:
            ids = np.arange(self.next_id, self.next_id + len(chunks), dtype="int64")
            self.index.add_with_ids(np.ascontiguousarray(vectors, dtype="float32"), ids)
            for i, c in zip(ids.tolist(), chunks):
                self.chunks[str(i)] = {**c, "doc_id": doc_id, "filename": filename}
            self.next_id += len(chunks)
            self.documents[doc_id] = {
                "doc_id": doc_id, "filename": filename, "file_hash": file_hash,
                "pages": pages, "chunks": len(chunks), "ids": ids.tolist(),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save()
            return ids.tolist()

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            doc = self.documents.pop(doc_id, None)
            if not doc:
                return False
            self.index.remove_ids(np.array(doc["ids"], dtype="int64"))
            for i in doc["ids"]:
                self.chunks.pop(str(i), None)
            self._save()
            return True

    def reset(self):
        with self._lock:
            self.index = self._new_index()
            self.chunks, self.documents, self.next_id = {}, {}, 0
            self._save()

    # reads
    def find_by_hash(self, file_hash: str) -> dict | None:
        return next((d for d in self.documents.values() if d["file_hash"] == file_hash), None)

    def search(self, query_vec: np.ndarray, k: int) -> list[dict]:
        with self._lock:
            if self.index.ntotal == 0:
                return []
            scores, ids = self.index.search(query_vec.reshape(1, -1).astype("float32"),
                                            min(k, self.index.ntotal))
            return [{**self.chunks[str(i)], "id": int(i), "score": float(s)}
                    for s, i in zip(scores[0], ids[0]) if i != -1]

    def get_chunks(self, doc_id: str) -> list[dict]:
        doc = self.documents.get(doc_id)
        return [self.chunks[str(i)] for i in doc["ids"]] if doc else []

    def list_documents(self) -> list[dict]:
        return [{k: v for k, v in d.items() if k != "ids"} for d in self.documents.values()]

    def stats(self) -> dict:
        return {"vectors": int(self.index.ntotal), "documents": len(self.documents),
                "dim": self.dim, "index_type": "IndexIDMap2(IndexFlatIP)"}


_store: FaissStore | None = None
_store_lock = threading.Lock()


def get_store() -> FaissStore:
    from app.core.config import get_settings
    from app.core.embeddings import get_embedder

    global _store
    with _store_lock:
        if _store is None:
            _store = FaissStore(get_settings().vector_dir, get_embedder().dim)
        return _store


def reset_store_singleton():
    global _store
    with _store_lock:
        _store = None
