"""Shared helpers for the Reporting Engine."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "report"


def summarize_definition(definition: Dict[str, Any]) -> Dict[str, Any]:
    sections = definition.get("sections", [])
    kinds: Dict[str, int] = {}
    for s in sections:
        kinds[s.get("kind", "unknown")] = kinds.get(s.get("kind", "unknown"), 0) + 1
    return {"title": definition.get("title", ""), "section_count": len(sections), "kinds": kinds}


def paginate(items: List[Any], limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    return {"data": items[offset:offset + limit], "meta": {
        "total": len(items), "limit": limit, "offset": offset}}
