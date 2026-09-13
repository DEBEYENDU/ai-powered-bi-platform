from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChunkingConfig:
    chunk_size: int = 500
    chunk_overlap: int = 100
    min_chunk_size: int = 50
    max_chunk_size: int = 2000
    separator_priority: list[str] = field(
        default_factory=lambda: ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
    )


class ChunkingService:
    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[dict]:
        if not text or not text.strip():
            return []

        cleaned = text.strip()
        metadata = metadata or {}

        raw_chunks = self._split_by_separators(cleaned)
        merged = self._merge_small_chunks(raw_chunks)
        sized = self._enforce_size_limits(merged)
        overlapped = self._apply_overlap(sized)
        final = self._merge_small_chunks(overlapped)
        final = self._enforce_size_limits(final)

        result: list[dict] = []
        for idx, chunk_text in enumerate(final):
            chunk_metadata = dict(metadata)
            chunk_metadata["chunk_index"] = idx
            chunk_metadata["char_count"] = len(chunk_text)
            chunk_metadata["word_count"] = len(chunk_text.split())
            result.append(
                {
                    "text": chunk_text,
                    "chunk_index": idx,
                    "metadata": chunk_metadata,
                }
            )

        return result

    def _split_by_separators(self, text: str) -> list[str]:
        if len(text) <= self.config.chunk_size:
            return [text]

        for separator in self.config.separator_priority:
            parts = text.split(separator)
            if len(parts) <= 1:
                continue

            candidates: list[str] = []
            current = ""

            for i, part in enumerate(parts):
                test = current + part if not current else current + separator + part

                if len(test) > self.config.chunk_size and current:
                    candidates.append(current)
                    current = part
                else:
                    current = test

            if current:
                candidates.append(current)

            if len(candidates) > 1:
                return candidates

        return self._split_by_fixed_size(text)

    def _split_by_fixed_size(self, text: str) -> list[str]:
        chunks: list[str] = []
        size = self.config.chunk_size
        for start in range(0, len(text), size):
            chunks.append(text[start : start + size])
        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        if len(chunks) <= 1 or self.config.chunk_overlap <= 0:
            return chunks

        overlapped: list[str] = [chunks[0]]

        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            current = chunks[i]
            overlap_text = prev[-self.config.chunk_overlap :]

            if overlap_text and current:
                combined = overlap_text + current
                if len(combined) <= self.config.max_chunk_size:
                    overlapped.append(combined)
                else:
                    overlapped.append(current)
            else:
                overlapped.append(current)

        return overlapped

    def _merge_small_chunks(self, chunks: list[str]) -> list[str]:
        if not chunks:
            return []

        merged: list[str] = []
        current = ""

        for chunk in chunks:
            if not current:
                current = chunk
            elif len(current) + len(chunk) + 1 <= self.config.chunk_size:
                current = current + "\n" + chunk if current else chunk
            else:
                merged.append(current)
                current = chunk

        if current:
            merged.append(current)

        return merged

    def _enforce_size_limits(self, chunks: list[str]) -> list[str]:
        result: list[str] = []
        for chunk in chunks:
            if len(chunk) > self.config.max_chunk_size:
                result.extend(self._split_by_fixed_size(chunk))
            elif len(chunk) < self.config.min_chunk_size and result:
                prev = result[-1]
                if len(prev) + len(chunk) + 1 <= self.config.chunk_size:
                    result[-1] = prev + "\n" + chunk
                else:
                    result.append(chunk)
            else:
                result.append(chunk)
        return result
