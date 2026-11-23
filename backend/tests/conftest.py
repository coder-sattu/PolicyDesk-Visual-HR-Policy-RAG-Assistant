"""Offline test setup: hash embeddings + mock LLM + temp data dir."""
import os
import shutil
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
SAMPLE = BACKEND / "data" / "sample_docs" / "HR_Policy_Handbook.pdf"


@pytest.fixture(autouse=True)
def offline_env(tmp_path, monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", os.getenv("TEST_EMBEDDING_PROVIDER", "hash"))
    monkeypatch.setenv("LLM_PROVIDER", os.getenv("TEST_LLM_PROVIDER", "mock"))
    monkeypatch.setenv("SCORE_THRESHOLD", "0.1")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "sample_docs").mkdir()
    shutil.copy(SAMPLE, tmp_path / "sample_docs" / SAMPLE.name)

    from app.core import config, embeddings, vector_store
    config.get_settings.cache_clear()
    embeddings.reset_embedder()
    vector_store.reset_store_singleton()
    yield tmp_path
    config.get_settings.cache_clear()
    vector_store.reset_store_singleton()


@pytest.fixture
def sample_pdf(offline_env) -> Path:
    return offline_env / "sample_docs" / SAMPLE.name
