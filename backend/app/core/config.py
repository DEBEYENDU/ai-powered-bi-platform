"""Application configuration.

Uses ``pydantic-settings`` when installed; otherwise falls back to a plain
pydantic model populated from environment variables, so the module imports
cleanly in minimal environments (tests, docs builds).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

try:
    from pydantic_settings import BaseSettings as _BaseSettings  # type: ignore

    class _SettingsBase(_BaseSettings):
        model_config = {"env_file": ".env", "extra": "ignore"}  # type: ignore[attr-defined]

except Exception:  # pragma: no cover - fallback without pydantic-settings

    from pydantic import BaseModel as _SettingsBase  # type: ignore


class Settings(_SettingsBase):  # type: ignore[misc]
    app_name: str = "AI-Powered BI Platform"
    environment: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://bi:bi@localhost:5432/bi_platform")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    storage_path: str = os.getenv("STORAGE_PATH", "/tmp/storage")
    reports_path: str = os.getenv("REPORTS_PATH", "/tmp/reports")

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
