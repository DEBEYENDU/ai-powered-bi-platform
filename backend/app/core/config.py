"""Application configuration.

Resolution order for every setting:
1. Real process environment variables (highest priority — Docker/K8s/CI).
2. ``backend/.env`` file, located via an absolute path anchored at this file,
   so it loads no matter which directory the server starts from. (The old
   relative ``".env"`` silently missed the file when CWD was the repo root —
   the reason STORAGE_PATH was ignored on Windows.)
3. Cross-platform ``pathlib`` defaults under the backend directory.

Uses ``pydantic-settings`` when installed; otherwise falls back to a plain
pydantic model populated from the environment (with a tiny built-in .env
parser, so no extra dependency is needed for the fallback path).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# backend/ directory (this file is backend/app/core/config.py).
BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


def _load_dotenv_fallback(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE, # comments, optional quotes).

    Only sets variables that are not already present in the environment.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ[key] = value


def _default_storage() -> str:
    return os.getenv("STORAGE_PATH", str(BASE_DIR / "storage"))


def _default_reports() -> str:
    return os.getenv("REPORTS_PATH", str(BASE_DIR / "reports"))


try:
    from pydantic_settings import BaseSettings as _BaseSettings  # type: ignore

    class _SettingsBase(_BaseSettings):
        # Absolute path: loads backend/.env regardless of process CWD.
        model_config = {"env_file": str(ENV_FILE), "extra": "ignore"}  # type: ignore[attr-defined]

except ImportError:  # pragma: no cover - fallback without pydantic-settings
    from pydantic import BaseModel as _SettingsBase  # type: ignore

    _load_dotenv_fallback(ENV_FILE)


class Settings(_SettingsBase):  # type: ignore[misc]
    app_name: str = "AI-Powered BI Platform"
    environment: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://bi:bi@localhost:5432/bi_platform"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Cross-platform defaults (pathlib); overridable via env / backend/.env.
    storage_path: str = _default_storage()
    reports_path: str = _default_reports()

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

    # AI Chat settings
    ai_provider: str = os.getenv("AI_PROVIDER", "openai")
    ai_model: str = os.getenv("AI_MODEL", "gpt-4o-mini")
    ai_temperature: float = float(os.getenv("AI_TEMPERATURE", "0.7"))
    ai_max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "4096"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    lmstudio_base_url: str = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    azure_openai_deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Knowledge Base / RAG settings
    knowledge_max_upload_size: int = int(
        os.getenv("KNOWLEDGE_MAX_UPLOAD_SIZE", str(50 * 1024 * 1024))
    )  # 50MB
    knowledge_chunk_size: int = int(os.getenv("KNOWLEDGE_CHUNK_SIZE", "500"))
    knowledge_chunk_overlap: int = int(os.getenv("KNOWLEDGE_CHUNK_OVERLAP", "100"))
    knowledge_default_top_k: int = int(os.getenv("KNOWLEDGE_DEFAULT_TOP_K", "10"))
    knowledge_semantic_weight: float = float(os.getenv("KNOWLEDGE_SEMANTIC_WEIGHT", "0.7"))
    knowledge_keyword_weight: float = float(os.getenv("KNOWLEDGE_KEYWORD_WEIGHT", "0.3"))
    knowledge_embedding_model: str = os.getenv(
        "KNOWLEDGE_EMBEDDING_MODEL", "text-embedding-3-large"
    )
    knowledge_embedding_dimensions: int = int(os.getenv("KNOWLEDGE_EMBEDDING_DIMENSIONS", "1536"))
    knowledge_rag_model: str = os.getenv("KNOWLEDGE_RAG_MODEL", "")  # empty means use ai_model
    knowledge_indexing_retries: int = int(os.getenv("KNOWLEDGE_INDEXING_RETRIES", "3"))

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_dir(self) -> Path:
        """Storage directory, created on demand."""
        path = Path(self.storage_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def reports_dir(self) -> Path:
        """Reports directory, created on demand."""
        path = Path(self.reports_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
