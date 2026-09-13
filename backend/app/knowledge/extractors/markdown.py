from __future__ import annotations

import re

from app.knowledge.extractors.base import BaseExtractor, ExtractedContent


class MarkdownExtractor(BaseExtractor):
    HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def extract(self, file_path: str, filename: str) -> ExtractedContent:
        text = self._read_file(file_path)
        sections = self._extract_sections(text)

        return ExtractedContent(
            text=text,
            metadata={
                "filename": filename,
                "line_count": text.count("\n") + 1,
                "char_count": len(text),
                "sections": sections,
                "section_count": len(sections),
            },
            content_type="text/markdown",
        )

    def supported_types(self) -> list[str]:
        return ["text/markdown"]

    def _extract_sections(self, text: str) -> list[dict[str, object]]:
        sections: list[dict[str, object]] = []
        for match in self.HEADER_RE.finditer(text):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.start()
            end = match.end()
            next_match = self.HEADER_RE.search(text, end)
            if next_match:
                content = text[end : next_match.start()].strip()
            else:
                content = text[end:].strip()
            sections.append(
                {
                    "level": level,
                    "title": title,
                    "start_offset": start,
                    "end_offset": end + len(content),
                    "content_preview": content[:200] if content else "",
                }
            )
        return sections

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
