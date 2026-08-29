from abc import ABC, abstractmethod
from typing import AsyncIterator

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
    def __init__(self, base_path: str = "/tmp/storage"):
        self.base_path = base_path
    
    async def put(self, path: str, data: bytes) -> str:
        import os
        full_path = os.path.join(self.base_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
        return full_path
