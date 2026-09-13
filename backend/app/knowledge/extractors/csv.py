from __future__ import annotations

import csv
import io
from pathlib import Path

from app.knowledge.extractors.base import BaseExtractor, ExtractedContent


class CSVExtractor(BaseExtractor):
    def extract(self, file_path: str, filename: str) -> ExtractedContent:
        text, metadata = self._read_csv(file_path)
        metadata["filename"] = filename
        return ExtractedContent(
            text=text,
            metadata=metadata,
            content_type="text/csv",
        )

    def supported_types(self) -> list[str]:
        return ["text/csv"]

    def _read_csv(self, file_path: str) -> tuple[str, dict[str, object]]:
        delimiter = self._detect_delimiter(file_path)

        with open(file_path, encoding="utf-8", newline="") as f:
            content = f.read()

        reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            return "", {
                "row_count": 0,
                "column_count": 0,
                "delimiter": delimiter,
                "headers": [],
            }

        headers = rows[0] if rows else []
        text_parts: list[str] = []
        text_parts.append(" | ".join(headers))

        for row_num, row in enumerate(rows[1:], start=2):
            row_text = " | ".join(row)
            text_parts.append(f"[Row {row_num}] {row_text}")

        full_text = "\n".join(text_parts)

        return full_text, {
            "row_count": len(rows) - 1 if len(rows) > 1 else 0,
            "column_count": len(headers),
            "delimiter": delimiter,
            "headers": headers,
            "total_characters": len(full_text),
        }

    @staticmethod
    def _detect_delimiter(file_path: str) -> str:
        with open(file_path, encoding="utf-8") as f:
            sample = f.read(8192)

        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
        except csv.Error:
            extension = Path(file_path).suffix.lower()
            delimiter_map = {
                ".csv": ",",
                ".tsv": "\t",
                ".ssv": ";",
            }
            return delimiter_map.get(extension, ",")
