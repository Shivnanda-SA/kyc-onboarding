from __future__ import annotations

from pathlib import Path
import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Always load the backend-specific .env regardless of the current working directory.
    # settings.py is at: backend/app/settings.py -> backend root is one parent up.
    _backend_root = Path(__file__).resolve().parents[1]
    _env_path = _backend_root / ".env"
    model_config = SettingsConfigDict(
        env_file=str(_env_path),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    data_dir: Path = Field(default=Path("../data"), alias="DATA_DIR")
    upload_dir: Path = Field(default=Path("../data/uploads"), alias="UPLOAD_DIR")
    sqlite_path: Path = Field(default=Path("../data/app.db"), alias="SQLITE_PATH")
    chroma_dir: Path = Field(default=Path("../data/chroma"), alias="CHROMA_DIR")

    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-5.2", alias="OPENAI_MODEL")

    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()

# Helpful startup signal for POC debugging.
logger.info(
    "Settings loaded. OPENAI_API_KEY set: %s | model: %s | env: %s",
    bool(settings.openai_api_key),
    settings.openai_model,
    settings.app_env,
)

