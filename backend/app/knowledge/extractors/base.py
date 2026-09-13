from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedContent:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    content_type: str = "text"


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str, filename: str) -> ExtractedContent:
        """Extract text and metadata from a file."""
        ...

    @abstractmethod
    def supported_types(self) -> list[str]:
        """Return list of supported content types."""
        ...
