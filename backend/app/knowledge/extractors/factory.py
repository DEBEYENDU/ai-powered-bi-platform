from __future__ import annotations

from pathlib import Path

from app.knowledge.extractors.base import BaseExtractor
from app.knowledge.extractors.csv import CSVExtractor
from app.knowledge.extractors.docx import DocxExtractor
from app.knowledge.extractors.markdown import MarkdownExtractor
from app.knowledge.extractors.pdf import PDFExtractor
from app.knowledge.extractors.text import TextExtractor


class ExtractorFactory:
    _extractors: dict[str, type[BaseExtractor]] = {
        ".txt": TextExtractor,
        ".text": TextExtractor,
        ".md": MarkdownExtractor,
        ".markdown": MarkdownExtractor,
        ".pdf": PDFExtractor,
        ".docx": DocxExtractor,
        ".doc": DocxExtractor,
        ".csv": CSVExtractor,
    }

    @classmethod
    def get_extractor(cls, filename: str) -> BaseExtractor:
        ext = Path(filename).suffix.lower()
        extractor_cls = cls._extractors.get(ext)
        if not extractor_cls:
            raise ValueError(f"Unsupported document type: {ext}")
        return extractor_cls()

    @classmethod
    def supported_types(cls) -> list[str]:
        return list(cls._extractors.keys())
