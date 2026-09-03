"""Admin helpers: pagination envelopes, redaction, license info."""

from __future__ import annotations

from typing import Any, Dict, List


def page(items: List[Any], limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    return {"data": items[offset:offset + limit],
            "meta": {"total": len(items), "limit": limit, "offset": offset}}


def redact(record: Dict[str, Any], secrets: tuple = ("password_hash", "api_key")) -> Dict[str, Any]:
    return {k: ("***" if k in secrets else v) for k, v in record.items()}


def license_info() -> Dict[str, Any]:
    return {"product": "AI-Powered BI Platform", "edition": "academic",
            "terms": "SPVP SBCPOE Indapur — no commercial use without permission"}
