"""Shared helpers for turning raw LLM replies into structured data.

Models frequently wrap JSON in ```json fences (and just as frequently do
not), so every caller that asks for JSON must go through this parser instead
of checking ``text.startswith("{")``.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$")


def parse_json_reply(text: str) -> Any | None:
    """Parse JSON out of a model reply, tolerating markdown code fences.

    Returns ``None`` when the reply does not contain valid JSON.
    """
    if not text:
        return None
    candidate = _FENCE_RE.sub("", text.strip()).strip()
    candidates = [candidate]
    start, end = candidate.find("{"), candidate.rfind("}")
    if 0 <= start < end:
        candidates.append(candidate[start : end + 1])
    start, end = candidate.find("["), candidate.rfind("]")
    if 0 <= start < end:
        candidates.append(candidate[start : end + 1])
    for attempt in candidates:
        if not attempt:
            continue
        try:
            return json.loads(attempt)
        except (ValueError, TypeError):
            continue
    return None
