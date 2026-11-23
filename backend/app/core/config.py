from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "HR Policy RAG"
    environment: str = "development"

    # LLM
    llm_provider: str = "groq"  # groq | mock
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 700

    # Embeddings
    embedding_provider: str = "fastembed"  # fastembed | hash
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_batch_size: int = 16

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 120

    # Retrieval
    top_k: int = 4
    score_threshold: float = 0.45

    # Storage
    data_dir: Path = BACKEND_DIR / "data"
    max_upload_mb: int = 20

    # API
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    frontend_dist: Path = BACKEND_DIR.parent / "frontend" / "dist"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def vector_dir(self) -> Path:
        return self.data_dir / "vector_store"

    @property
    def model_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def sample_doc(self) -> Path:
        return self.data_dir / "sample_docs" / "HR_Policy_Handbook.pdf"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
