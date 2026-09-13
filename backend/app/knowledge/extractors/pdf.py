from __future__ import annotations

from pypdf import PdfReader

from app.knowledge.extractors.base import BaseExtractor, ExtractedContent


class PDFExtractor(BaseExtractor):
    def extract(self, file_path: str, filename: str) -> ExtractedContent:
        try:
            reader = PdfReader(file_path)
        except Exception as exc:
            return ExtractedContent(
                text=f"[ERROR] Could not read PDF: {exc}",
                metadata={
                    "filename": filename,
                    "error": str(exc),
                    "page_count": 0,
                },
                content_type="application/pdf",
            )

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return ExtractedContent(
                    text="[ERROR] PDF is encrypted and could not be decrypted",
                    metadata={
                        "filename": filename,
                        "error": "encrypted",
                        "page_count": len(reader.pages),
                    },
                    content_type="application/pdf",
                )

        page_texts: list[str] = []
        page_numbers: list[int] = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            page_texts.append(text)
            page_numbers.append(i + 1)

        full_text = "\n\n".join(f"[Page {pn}]\n{pt}" for pn, pt in zip(page_numbers, page_texts))

        return ExtractedContent(
            text=full_text,
            metadata={
                "filename": filename,
                "page_count": len(reader.pages),
                "page_numbers": page_numbers,
                "total_characters": len(full_text),
            },
            content_type="application/pdf",
        )

    def supported_types(self) -> list[str]:
        return ["application/pdf"]
