"""Storage abstraction (local provider + future S3/MinIO).

All paths are ``pathlib.Path``; the default root comes from application
settings (``STORAGE_PATH`` env / ``backend/.env``), never a hardcoded
OS-specific literal.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


def _default_base_path() -> Path:
    try:
        from app.core.config import get_settings

        return Path(get_settings().storage_path)
    except ImportError:
        # Settings module unavailable (minimal envs): backend-local fallback.
        return Path(__file__).resolve().parents[3] / "storage"


class StorageProvider(ABC):
    @abstractmethod
    async def put(self, path: str, data: bytes) -> str: ...
    @abstractmethod
    async def get(self, path: str) -> bytes: ...
    @abstractmethod
    async def delete(self, path: str) -> None: ...
    @abstractmethod
    async def exists(self, path: str) -> bool: ...


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str | Path | None = None):
        self.base_path = Path(base_path) if base_path is not None else _default_base_path()

    def _resolve(self, path: str) -> Path:
        # Guard against absolute-path escapes outside the storage root.
        full = (self.base_path / path).resolve()
        root = self.base_path.resolve()
        if root not in full.parents and full != root:
            raise ValueError(f"Path escapes storage root: {path!r}")
        return full

    async def put(self, path: str, data: bytes) -> str:
        full_path = self._resolve(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return str(full_path)

    async def get(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    async def delete(self, path: str) -> None:
        self._resolve(path).unlink(missing_ok=True)

    async def exists(self, path: str) -> bool:
        return self._resolve(path).exists()
