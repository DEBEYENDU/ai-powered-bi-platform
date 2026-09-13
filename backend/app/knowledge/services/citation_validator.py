from __future__ import annotations

import re

from app.knowledge.schemas.answer import CitationSource


class CitationValidator:
    @staticmethod
    def validate_answer(
        answer: str, sources: list[CitationSource]
    ) -> tuple[str, list[CitationSource], list[str]]:
        warnings: list[str] = []
        referenced = CitationValidator.extract_citations(answer)

        valid_indices = set(range(1, len(sources) + 1))
        invalid_refs = [r for r in referenced if r not in valid_indices]

        for ref in invalid_refs:
            warnings.append(f"Citation [Source {ref}] references non-existent source")

        cleaned = CitationValidator.remove_invalid_citations(answer, valid_indices)

        valid_sources = [sources[i - 1] for i in referenced if i in valid_indices]
        seen_ids: set[int] = set()
        deduped: list[CitationSource] = []
        for s in valid_sources:
            cid = id(s)
            if cid not in seen_ids:
                seen_ids.add(cid)
                deduped.append(s)

        return cleaned, deduped, warnings

    @staticmethod
    def extract_citations(answer: str) -> list[int]:
        pattern = r"\[Source\s+(\d+)\]"
        matches = re.findall(pattern, answer)
        return [int(m) for m in matches]

    @staticmethod
    def remove_invalid_citations(answer: str, valid_indices: set[int]) -> str:
        def _replace(match: re.Match) -> str:
            n = int(match.group(1))
            return match.group(0) if n in valid_indices else ""

        return re.sub(r"\[Source\s+(\d+)\]", _replace, answer)
