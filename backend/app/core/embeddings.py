"""Embedding providers. All return L2-normalised float32 vectors."""
import hashlib
import re
import threading
from abc import ABC, abstractmethod

import numpy as np

from app.core.config import get_settings


def _normalize(vecs: np.ndarray) -> np.ndarray:
    vecs = np.asarray(vecs, dtype="float32")
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


class Embedder(ABC):
    name: str
    dim: int

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray: ...


class FastEmbedEmbedder(Embedder):
    """Local ONNX model (no torch). Downloads once from HuggingFace."""

    def __init__(self, model_name: str, cache_dir: str | None = None):
        from fastembed import TextEmbedding

        self.name = model_name
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        self.dim = len(next(iter(self._model.query_embed(["dim probe"]))))

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return _normalize(np.array(list(self._model.passage_embed(texts))))

    def embed_query(self, text: str) -> np.ndarray:
        return _normalize(np.array(list(self._model.query_embed([text]))))[0]


class HashEmbedder(Embedder):
    """Offline fallback: hashed word uni+bigrams. For tests only."""

    _token = re.compile(r"[a-z0-9]+")

    def __init__(self, dim: int = 512):
        self.name = f"hash-{dim}"
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        words = [w[:-1] if len(w) > 3 and w.endswith("s") else w  # crude stem
                 for w in self._token.findall(text.lower())]
        feats = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
        v = np.zeros(self.dim, dtype="float32")
        for f in feats:
            h = int(hashlib.md5(f.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
        return np.sign(v) * np.log1p(np.abs(v))

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return _normalize(np.stack([self._vec(t) for t in texts]))

    def embed_query(self, text: str) -> np.ndarray:
        return _normalize(self._vec(text)[None, :])[0]


_lock = threading.Lock()
_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    with _lock:
        if _embedder is None:
            s = get_settings()
            if s.embedding_provider == "hash":
                _embedder = HashEmbedder()
            else:
                _embedder = FastEmbedEmbedder(s.embedding_model, str(s.model_dir))
        return _embedder


def reset_embedder() -> None:
    global _embedder
    with _lock:
        _embedder = None
