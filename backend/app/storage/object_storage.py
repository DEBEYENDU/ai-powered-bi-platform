"""Object storage abstraction — provider-neutral interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)


class ObjectStorage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        ...

    @abstractmethod
    def get(self, key: str) -> bytes | None:
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        ...

    @abstractmethod
    def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        ...


class LocalObjectStorage(ObjectStorage):
    def __init__(self, base_path: str | Path) -> None:
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        return self.base / key

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def get(self, key: str) -> bytes | None:
        path = self._resolve(key)
        if path.exists():
            return path.read_bytes()
        return None

    def delete(self, key: str) -> bool:
        path = self._resolve(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def list_keys(self, prefix: str = "") -> list[str]:
        keys = []
        for f in self.base.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(self.base))
                if not prefix or rel.startswith(prefix):
                    keys.append(rel)
        return keys

    def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        return None


class CloudObjectStorage(ObjectStorage):
    def __init__(self, bucket: str, **kwargs: Any) -> None:
        self.bucket = bucket
        log.warning("cloud_object_storage_not_implemented", bucket=bucket)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError("Cloud storage not yet implemented")

    def get(self, key: str) -> bytes | None:
        raise NotImplementedError("Cloud storage not yet implemented")

    def delete(self, key: str) -> bool:
        raise NotImplementedError("Cloud storage not yet implemented")

    def exists(self, key: str) -> bool:
        raise NotImplementedError("Cloud storage not yet implemented")

    def list_keys(self, prefix: str = "") -> list[str]:
        raise NotImplementedError("Cloud storage not yet implemented")

    def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        raise NotImplementedError("Cloud storage not yet implemented")
