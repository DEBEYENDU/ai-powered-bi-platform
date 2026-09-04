"""Admin helpers: pagination envelopes, redaction, license info."""

from __future__ import annotations

from typing import Any


def page(items: list[Any], limit: int = 50, offset: int = 0) -> dict[str, Any]:
    return {
        "data": items[offset : offset + limit],
        "meta": {"total": len(items), "limit": limit, "offset": offset},
    }


def redact(record: dict[str, Any], secrets: tuple = ("password_hash", "api_key")) -> dict[str, Any]:
    return {k: ("***" if k in secrets else v) for k, v in record.items()}


def license_info() -> dict[str, Any]:
    return {
        "product": "AI-Powered BI Platform",
        "edition": "academic",
        "terms": "SPVP SBCPOE Indapur — no commercial use without permission",
    }
