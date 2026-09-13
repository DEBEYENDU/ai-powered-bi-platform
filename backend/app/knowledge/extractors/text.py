from __future__ import annotations

from app.knowledge.extractors.base import BaseExtractor, ExtractedContent


class TextExtractor(BaseExtractor):
    def extract(self, file_path: str, filename: str) -> ExtractedContent:
        text = self._read_file(file_path)
        return ExtractedContent(
            text=text,
            metadata={
                "filename": filename,
                "encoding": self._detect_encoding(file_path),
                "line_count": text.count("\n") + 1,
                "char_count": len(text),
            },
            content_type="text/plain",
        )

    def supported_types(self) -> list[str]:
        return ["text/plain"]

    @staticmethod
    def _read_file(file_path: str) -> str:
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                import chardet

                with open(file_path, "rb") as f:
                    raw = f.read()
                detected = chardet.detect(raw)
                encoding = detected.get("encoding") or "latin-1"
                return raw.decode(encoding, errors="replace")
            except ImportError:
                with open(file_path, encoding="latin-1") as f:
                    return f.read()

    @staticmethod
    def _detect_encoding(file_path: str) -> str:
        try:
            import chardet

            with open(file_path, "rb") as f:
                raw = f.read(8192)
            detected = chardet.detect(raw)
            return detected.get("encoding") or "utf-8"
        except ImportError:
            try:
                with open(file_path, encoding="utf-8"):
                    return "utf-8"
            except UnicodeDecodeError:
                return "latin-1"
