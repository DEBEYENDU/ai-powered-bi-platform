"""Comprehensive data profiler — computes statistics, infers column types,
detects quality issues, and generates column profiles."""

from __future__ import annotations

import re
import time
from typing import Any

import numpy as np
import pandas as pd

from app.ai.data_engineering.schemas import (
    ColumnProfile,
    QualityScore,
    Relationship,
    RelationshipGraph,
)

# ---------------------------------------------------------------------------
# Regex helpers for semantic type detection
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^[\+]?[\d\s\-\(\)]{7,15}$")
_URL_RE = re.compile(r"^https?://")
_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_DATE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}")
_CURRENCY_RE = re.compile(r"^[\$€£¥₹][\s]?[\d,]+\.?\d*$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _detect_semantic_type(series: pd.Series) -> str:
    """Infer the semantic type of a pandas Series from a sample of non-null values."""
    sample = series.dropna().head(200)
    if len(sample) == 0:
        return "unknown"

    vals = sample.astype(str).tolist()
    n = len(vals)

    # Boolean
    unique_str = {v.lower().strip() for v in vals}
    if unique_str <= {"true", "false", "1", "0", "yes", "no"}:
        return "boolean"

    # Email
    if sum(1 for v in vals if _EMAIL_RE.match(v)) / n > 0.8:
        return "email"

    # Phone
    if sum(1 for v in vals if _PHONE_RE.match(v)) / n > 0.8:
        return "phone"

    # URL
    if sum(1 for v in vals if _URL_RE.match(v)) / n > 0.8:
        return "url"

    # IP
    if sum(1 for v in vals if _IP_RE.match(v)) / n > 0.8:
        return "ip_address"

    # UUID
    if sum(1 for v in vals if _UUID_RE.match(v)) / n > 0.8:
        return "uuid"

    # Currency
    if sum(1 for v in vals if _CURRENCY_RE.match(v)) / n > 0.6:
        return "currency"

    # Date
    try:
        pd.to_datetime(sample.head(50), infer_datetime_format=True)
        return "date"
    except (ValueError, TypeError):
        pass

    # Numeric
    try:
        numeric = pd.to_numeric(sample, errors="coerce")
        if numeric.notna().sum() / n > 0.8:
            return "numeric"
    except Exception:
        pass

    # Categorical (low cardinality)
    if series.nunique() / max(len(sample), 1) < 0.1:
        return "category"

    return "text"


def _infer_purpose(name: str, semantic_type: str, profile: ColumnProfile) -> str:
    """Infer a business purpose for a column."""
    lower = name.lower().strip()

    if semantic_type == "uuid" or "id" in lower:
        if "primary" in lower or (lower.endswith("_id") and "foreign" not in lower):
            return "primary_key"
        if "foreign" in lower or (lower.endswith("_id") and lower != "id"):
            return "foreign_key"
        return "identifier"

    if semantic_type == "date":
        return "temporal"
    if semantic_type == "currency":
        return "monetary_measure"
    if semantic_type == "email":
        return "contact_email"
    if semantic_type == "phone":
        return "contact_phone"
    if semantic_type == "boolean":
        return "flag_indicator"
    if semantic_type == "category":
        return "dimension"
    if semantic_type == "numeric":
        if profile.std_value and profile.mean_value:
            cv = abs(profile.std_value / profile.mean_value) if profile.mean_value != 0 else 0
            if cv < 0.5:
                return "measurement"
            return "measure"
        return "measure"
    if semantic_type == "text":
        if profile.mean_value and profile.mean_value > 50:
            return "description"
        return "label"

    return "attribute"


# ---------------------------------------------------------------------------
# Column profiler
# ---------------------------------------------------------------------------


def _profile_numeric(series: pd.Series) -> dict[str, Any]:
    """Compute numeric statistics for a Series."""
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric) == 0:
        return {}
    stats: dict[str, Any] = {
        "min_value": float(numeric.min()),
        "max_value": float(numeric.max()),
        "mean_value": float(numeric.mean()),
        "median_value": float(numeric.median()),
        "std_value": float(numeric.std()) if len(numeric) > 1 else 0.0,
    }
    try:
        stats["skewness"] = float(numeric.skew())
        stats["kurtosis"] = float(numeric.kurtosis())
    except Exception:
        pass
    return stats


def _profile_categorical(series: pd.Series) -> list[dict[str, Any]]:
    """Return top N value counts."""
    vc = series.value_counts().head(10)
    return [{"value": str(v), "count": int(c)} for v, c in vc.items()]


def profile_column(series: pd.Series) -> ColumnProfile:
    """Generate a complete ColumnProfile for a single pandas Series."""
    name = str(series.name) if series.name is not None else ""
    total = len(series)
    null_count = int(series.isna().sum())
    non_null_count = total - null_count
    unique_count = int(series.nunique())
    dup_count = int(total - unique_count - null_count)

    semantic_type = _detect_semantic_type(series)

    profile = ColumnProfile(
        name=name,
        dtype=str(series.dtype),
        non_null_count=non_null_count,
        null_count=null_count,
        null_pct=round(null_count / total * 100, 2) if total > 0 else 0.0,
        unique_count=unique_count,
        unique_pct=round(unique_count / total * 100, 2) if total > 0 else 0.0,
        duplicate_count=max(dup_count, 0),
        duplicate_pct=round(max(dup_count, 0) / total * 100, 2) if total > 0 else 0.0,
        top_values=_profile_categorical(series.dropna()),
        inferred_type=semantic_type,
        detected_format="",
    )

    if semantic_type == "numeric":
        num_stats = _profile_numeric(series)
        profile.min_value = num_stats.get("min_value")
        profile.max_value = num_stats.get("max_value")
        profile.mean_value = num_stats.get("mean_value")
        profile.median_value = num_stats.get("median_value")
        profile.std_value = num_stats.get("std_value")
        profile.skewness = num_stats.get("skewness")
        profile.kurtosis = num_stats.get("kurtosis")
    else:
        non_null = series.dropna()
        if len(non_null) > 0:
            profile.min_value = str(non_null.min())
            profile.max_value = str(non_null.max())

    purpose = _infer_purpose(name, semantic_type, profile)
    profile.detected_format = purpose

    return profile


# ---------------------------------------------------------------------------
# Dataset profiler
# ---------------------------------------------------------------------------


def profile_dataset(df: pd.DataFrame, name: str = "") -> dict[str, Any]:
    """Profile an entire DataFrame. Returns a dict suitable for ProfileResponse."""
    t0 = time.perf_counter()

    columns = [profile_column(df[col]) for col in df.columns]

    total_cells = len(df) * len(df.columns) if len(df.columns) > 0 else 0
    missing_cells = int(df.isna().sum().sum())

    # Duplicate rows
    dup_rows = int(df.duplicated().sum())

    # Quality score components
    completeness = round((1 - missing_cells / total_cells) * 100, 1) if total_cells > 0 else 100.0
    uniqueness = round((1 - dup_rows / len(df)) * 100, 1) if len(df) > 0 else 100.0

    # Consistency: check for mixed types per column
    consistency_scores: list[float] = []
    for col in df.columns:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            consistency_scores.append(100.0)
            continue
        types = non_null.map(type).nunique()
        consistency_scores.append(round(max(0, 100 - (types - 1) * 30), 1))
    consistency = round(float(np.mean(consistency_scores)), 1) if consistency_scores else 100.0

    # Validity: check column-level validity
    validity_scores: list[float] = []
    for col in columns:
        if col.null_pct > 50:
            validity_scores.append(max(0, 100 - col.null_pct))
        else:
            validity_scores.append(max(0, 100 - col.null_pct * 0.5))
    validity = round(float(np.mean(validity_scores)), 1) if validity_scores else 100.0

    # Timeliness: check for date columns
    date_cols = [c for c in columns if c.inferred_type == "date"]
    timeliness = max(50.0, 100.0 - len(date_cols) * 2) if date_cols else 85.0

    overall = round(
        completeness * 0.25
        + uniqueness * 0.20
        + consistency * 0.20
        + validity * 0.20
        + timeliness * 0.15,
        1,
    )

    quality_score = QualityScore(
        overall=overall,
        completeness=completeness,
        consistency=consistency,
        accuracy=round(validity * 0.9 + uniqueness * 0.1, 1),
        uniqueness=uniqueness,
        validity=validity,
        timeliness=timeliness,
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    return {
        "dataset_id": "",
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "duplicates": dup_rows,
        "missing_cells": missing_cells,
        "quality_score": quality_score,
        "profile_time_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Relationship discovery
# ---------------------------------------------------------------------------


def discover_relationships(tables: dict[str, pd.DataFrame]) -> list[Relationship]:
    """Discover relationships between multiple DataFrames by name matching and value overlap."""
    relationships: list[Relationship] = []
    table_names = list(tables.keys())

    for i, t1_name in enumerate(table_names):
        t1 = tables[t1_name]
        for col1 in t1.columns:
            col1_lower = col1.lower().strip()
            for t2_name in table_names[i + 1 :]:
                t2 = tables[t2_name]
                for col2 in t2.columns:
                    col2_lower = col2.lower().strip()

                    # Exact name match (e.g. customer_id in both)
                    if col1_lower == col2_lower and col1_lower.endswith("_id"):
                        # Check value overlap
                        common = set(t1[col1].dropna().unique()) & set(t2[col2].dropna().unique())
                        total_unique = max(len(t1[col1].dropna().unique()), 1)
                        confidence = min(len(common) / total_unique, 1.0)

                        if confidence > 0.3:
                            rel_type = "many_to_one"
                            if t1[col1].nunique() == len(t1) and t2[col2].nunique() == len(t2):
                                rel_type = "one_to_one"
                            relationships.append(
                                Relationship(
                                    source_table=t1_name,
                                    source_column=col1,
                                    target_table=t2_name,
                                    target_column=col2,
                                    relationship_type=rel_type,
                                    confidence=round(confidence, 3),
                                    evidence=[f"Name match and {len(common)} overlapping values"],
                                )
                            )

                    # Suffix pattern: e.g. customer_id in orders → customer.id
                    elif col1_lower.endswith("_id") and col2_lower in (
                        "id",
                        col1_lower.replace("_id", ""),
                    ):
                        common = set(t1[col1].dropna().unique()) & set(t2[col2].dropna().unique())
                        if len(common) > 0:
                            confidence = min(
                                len(common) / max(len(t1[col1].dropna().unique()), 1), 1.0
                            )
                            if confidence > 0.3:
                                relationships.append(
                                    Relationship(
                                        source_table=t1_name,
                                        source_column=col1,
                                        target_table=t2_name,
                                        target_column=col2,
                                        relationship_type="many_to_one",
                                        confidence=round(confidence, 3),
                                        evidence=[
                                            f"Suffix pattern match, {len(common)} overlapping values"
                                        ],
                                    )
                                )

    return relationships


def build_relationship_graph(
    tables: dict[str, pd.DataFrame], relationships: list[Relationship]
) -> RelationshipGraph:
    """Build a relationship graph for visualization."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for t_name, df in tables.items():
        nodes.append(
            {
                "id": t_name,
                "label": t_name,
                "rows": len(df),
                "columns": len(df.columns),
            }
        )

    for rel in relationships:
        edge_id = f"{rel.source_table}.{rel.source_column}->{rel.target_table}.{rel.target_column}"
        edges.append(
            {
                "id": edge_id,
                "source": rel.source_table,
                "target": rel.target_table,
                "source_column": rel.source_column,
                "target_column": rel.target_column,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence,
                "label": f"{rel.source_column} → {rel.target_column}",
            }
        )

    # Determine schema type
    schema_type = "denormalized"
    if len(relationships) >= 2:
        # Star: one table connects to many others
        from collections import Counter

        table_counts: Counter[str] = Counter()
        for r in relationships:
            table_counts[r.source_table] += 1
            table_counts[r.target_table] += 1
        max_connections = max(table_counts.values()) if table_counts else 0
        if max_connections >= len(tables) - 1:
            schema_type = "star_schema"
        elif len(relationships) >= len(tables):
            schema_type = "snowflake_schema"

    return RelationshipGraph(
        nodes=nodes,
        edges=edges,
        schema_type=schema_type,
    )
