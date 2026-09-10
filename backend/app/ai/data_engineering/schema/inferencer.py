"""Schema inference — detect column types, infer primary/foreign keys,
and generate a human-readable schema summary."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.ai.data_engineering.schemas import SchemaInfo

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^[\+]?[\d\s\-\(\)]{7,15}$")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def infer_column_schema(series: pd.Series, col_name: str) -> dict[str, Any]:
    """Infer detailed schema for a single column."""
    total = len(series)
    non_null = series.dropna()
    null_count = total - len(non_null)

    # Semantic type
    semantic_type = "text"
    lower = col_name.lower().strip()

    if "id" in lower:
        semantic_type = "id"
    elif "date" in lower or "time" in lower or "created" in lower or "updated" in lower:
        semantic_type = "date"
    elif any(k in lower for k in ("email", "mail")):
        semantic_type = "email"
    elif any(k in lower for k in ("phone", "tel", "mobile")):
        semantic_type = "phone"
    elif any(k in lower for k in ("revenue", "amount", "price", "total", "cost")):
        semantic_type = "currency"
    elif any(k in lower for k in ("name", "title", "label")):
        semantic_type = "name"
    elif any(k in lower for k in ("country", "city", "state", "region")):
        semantic_type = "location"
    elif any(k in lower for k in ("category", "type", "status")):
        semantic_type = "category"
    elif series.dtype == "bool":
        semantic_type = "boolean"
    elif pd.api.types.is_numeric_dtype(series):
        semantic_type = "numeric"
    else:
        # Sample-based detection
        if len(non_null) > 0:
            sample = non_null.head(100).astype(str)
            email_match = sample.str.match(_EMAIL_RE, na=False).mean()
            phone_match = sample.str.match(_PHONE_RE, na=False).mean()
            uuid_match = sample.str.match(_UUID_RE, na=False).mean()

            if email_match > 0.8:
                semantic_type = "email"
            elif phone_match > 0.8:
                semantic_type = "phone"
            elif uuid_match > 0.8:
                semantic_type = "uuid"
            else:
                try:
                    pd.to_datetime(non_null.head(20), infer_datetime_format=True)
                    semantic_type = "date"
                except (ValueError, TypeError):
                    try:
                        pd.to_numeric(non_null.head(20), errors="raise")
                        semantic_type = "numeric"
                    except (ValueError, TypeError):
                        if non_null.nunique() / max(len(non_null), 1) < 0.1:
                            semantic_type = "category"

    # Key likelihood
    key_likelihood = "none"
    if semantic_type == "id" or lower.endswith("_id"):
        if non_null.nunique() == len(non_null) and null_count == 0:
            key_likelihood = "primary"
        elif null_count == 0:
            key_likelihood = "candidate"
    elif lower.endswith("_id") or "foreign" in lower:
        key_likelihood = "foreign"

    # Statistics
    stats: dict[str, Any] = {
        "dtype": str(series.dtype),
        "semantic_type": semantic_type,
        "null_count": null_count,
        "null_pct": round(null_count / max(total, 1) * 100, 2),
        "unique_count": int(series.nunique()),
        "unique_pct": round(series.nunique() / max(total, 1) * 100, 2),
        "key_likelihood": key_likelihood,
    }

    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if len(numeric) > 0:
            stats["min"] = float(numeric.min())
            stats["max"] = float(numeric.max())
            stats["mean"] = float(numeric.mean())
            stats["std"] = float(numeric.std()) if len(numeric) > 1 else 0
    elif series.dtype == object and len(non_null) > 0:
        sample_str = non_null.astype(str)
        stats["avg_length"] = round(float(sample_str.str.len().mean()), 1)
        stats["max_length"] = int(sample_str.str.len().max())

    return {
        "name": col_name,
        "semantic_type": semantic_type,
        "key_likelihood": key_likelihood,
        "stats": stats,
    }


def infer_table_schema(df: pd.DataFrame, table_name: str = "dataset") -> SchemaInfo:
    """Infer full table schema."""
    columns: list[dict[str, Any]] = []
    primary_keys: list[str] = []
    foreign_keys: list[dict[str, str]] = []

    for col in df.columns:
        col_info = infer_column_schema(df[col], col)
        columns.append(col_info)

        if col_info["key_likelihood"] == "primary":
            primary_keys.append(col)
        elif col_info["key_likelihood"] == "foreign":
            ref_table = col.lower().replace("_id", "")
            foreign_keys.append({"column": col, "references": ref_table})

    # Infer table purpose
    semantic_types = {c["semantic_type"] for c in columns}
    purpose = "dimension"
    if "currency" in semantic_types or ("numeric" in semantic_types and len(columns) > 4):
        purpose = "fact"
    elif len(primary_keys) == 0 and len(foreign_keys) > 0:
        purpose = "bridge"

    return SchemaInfo(
        table_name=table_name,
        columns=columns,
        primary_keys=primary_keys,
        foreign_keys=foreign_keys,
        row_count=len(df),
        inferred_purpose=purpose,
    )


def generate_schema_summary(schemas: list[SchemaInfo]) -> str:
    """Generate a human-readable summary of all table schemas."""
    parts: list[str] = []
    for s in schemas:
        parts.append(f"TABLE: {s.table_name} ({s.row_count} rows, {len(s.columns)} cols)")
        parts.append(f"  Purpose: {s.inferred_purpose}")
        if s.primary_keys:
            parts.append(f"  Primary Keys: {', '.join(s.primary_keys)}")
        if s.foreign_keys:
            fk_strs = [f"{fk['column']} → {fk['references']}" for fk in s.foreign_keys]
            parts.append(f"  Foreign Keys: {', '.join(fk_strs)}")
        parts.append("  Columns:")
        for c in s.columns:
            parts.append(
                f"    {c['name']}: {c['semantic_type']} ({c['stats'].get('dtype', '?')}) "
                f"nulls={c['stats'].get('null_pct', 0)}%"
            )
        parts.append("")
    return "\n".join(parts)
