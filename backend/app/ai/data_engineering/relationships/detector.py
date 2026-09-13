"""Advanced relationship detector — schema inference, foreign-key detection,
star/snowflake classification, and join recommendation."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from app.ai.data_engineering.schemas import Relationship, RelationshipGraph, SchemaInfo


def infer_schema(df: pd.DataFrame, table_name: str = "dataset") -> SchemaInfo:
    """Infer the schema of a single DataFrame."""
    columns: list[dict[str, Any]] = []
    primary_keys: list[str] = []
    foreign_keys: list[dict[str, str]] = []

    for col in df.columns:
        series = df[col]
        series.dropna()
        col_info: dict[str, Any] = {
            "name": col,
            "dtype": str(series.dtype),
            "null_pct": round(series.isna().sum() / max(len(series), 1) * 100, 2),
            "unique_count": int(series.nunique()),
            "semantic_type": _quick_semantic(series, col),
        }
        columns.append(col_info)

        col_lower = col.lower().strip()
        # Primary key heuristic
        if col_lower in ("id", f"{table_name}_id") or (
            col_lower.endswith("_id")
            and series.nunique() == len(series)
            and series.isna().sum() == 0
        ):
            primary_keys.append(col)

        # Foreign key heuristic
        if col_lower.endswith("_id") and col_lower != "id" and col_lower not in primary_keys:
            foreign_keys.append({"column": col, "references": col_lower.replace("_id", "")})

    return SchemaInfo(
        table_name=table_name,
        columns=columns,
        primary_keys=primary_keys,
        foreign_keys=foreign_keys,
        row_count=len(df),
        inferred_purpose=_infer_table_purpose(table_name, columns),
    )


def _quick_semantic(series: pd.Series, name: str) -> str:
    """Fast semantic type detection."""
    lower = name.lower().strip()
    if "id" in lower:
        return "identifier"
    if "date" in lower or "time" in lower or "created" in lower:
        return "date"
    if any(k in lower for k in ("revenue", "amount", "price", "total", "cost", "income")):
        return "currency"
    if any(k in lower for k in ("email", "mail")):
        return "email"
    if any(k in lower for k in ("phone", "tel", "mobile")):
        return "phone"
    if any(k in lower for k in ("name", "title", "label")):
        return "name"
    if any(k in lower for k in ("country", "city", "state", "region", "address")):
        return "location"
    if any(k in lower for k in ("category", "type", "status", "group")):
        return "category"
    if series.dtype in ("bool",):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "text"


def _infer_table_purpose(name: str, columns: list[dict[str, Any]]) -> str:
    """Determine if a table is a fact, dimension, or bridge table."""
    {c["name"].lower() for c in columns}
    semantic_types = {c.get("semantic_type", "") for c in columns}

    if "currency" in semantic_types or "numeric" in semantic_types:
        return "fact_table"
    if any(k in name.lower() for k in ("dim", "lookup", "reference")):
        return "dimension_table"
    if len(columns) <= 4 and "identifier" in semantic_types:
        return "bridge_table"
    return "dimension_table"


def detect_cross_table_relationships(
    tables: dict[str, pd.DataFrame],
) -> list[Relationship]:
    """Detect relationships across multiple tables."""
    relationships: list[Relationship] = []
    names = list(tables.keys())

    for i, n1 in enumerate(names):
        df1 = tables[n1]
        for col1 in df1.columns:
            col1_lower = col1.lower().strip()
            for n2 in names[i + 1 :]:
                df2 = tables[n2]
                for col2 in df2.columns:
                    col2_lower = col2.lower().strip()

                    # Same name + ends with _id
                    if col1_lower == col2_lower and col1_lower.endswith("_id"):
                        common = set(df1[col1].dropna()) & set(df2[col2].dropna())
                        total = max(len(df1[col1].dropna()), 1)
                        conf = min(len(common) / total, 1.0)
                        if conf > 0.25:
                            relationships.append(
                                Relationship(
                                    source_table=n1,
                                    source_column=col1,
                                    target_table=n2,
                                    target_column=col2,
                                    relationship_type="many_to_one",
                                    confidence=round(conf, 3),
                                    evidence=[f"{len(common)} overlapping values"],
                                )
                            )

                    # FK pattern: orders.customer_id → customers.id
                    elif col1_lower.endswith("_id") and col1_lower.replace("_id", "") == col2_lower:
                        common = set(df1[col1].dropna()) & set(df2[col2].dropna())
                        if len(common) > 0:
                            conf = min(len(common) / max(len(df1[col1].dropna()), 1), 1.0)
                            if conf > 0.25:
                                relationships.append(
                                    Relationship(
                                        source_table=n1,
                                        source_column=col1,
                                        target_table=n2,
                                        target_column=col2,
                                        relationship_type="many_to_one",
                                        confidence=round(conf, 3),
                                        evidence=[f"FK pattern: {col1} → {col2}"],
                                    )
                                )

    return relationships


def classify_schema_type(
    tables: dict[str, pd.DataFrame],
    relationships: list[Relationship],
) -> str:
    """Classify overall schema as star, snowflake, or denormalized."""
    if not relationships:
        return "denormalized"

    # Count connections per table
    conn_count: Counter[str] = Counter()
    for r in relationships:
        conn_count[r.source_table] += 1
        conn_count[r.target_table] += 1

    max_conn = max(conn_count.values())
    n_tables = len(tables)

    # Star: one central fact table connected to many dimensions
    if max_conn >= n_tables - 1:
        return "star_schema"

    # Snowflake: multi-level hierarchy
    if len(relationships) >= n_tables:
        return "snowflake_schema"

    return "denormalized"


def build_schema_graph(
    tables: dict[str, pd.DataFrame],
    relationships: list[Relationship],
) -> RelationshipGraph:
    """Build a graph of all tables and their relationships."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for t_name, df in tables.items():
        schema = infer_schema(df, t_name)
        nodes.append(
            {
                "id": t_name,
                "label": t_name,
                "rows": len(df),
                "columns": len(df.columns),
                "purpose": schema.inferred_purpose,
                "primary_keys": schema.primary_keys,
                "foreign_keys": schema.foreign_keys,
            }
        )

    for rel in relationships:
        edges.append(
            {
                "id": f"{rel.source_table}.{rel.source_column}->{rel.target_table}.{rel.target_column}",
                "source": rel.source_table,
                "target": rel.target_table,
                "source_column": rel.source_column,
                "target_column": rel.target_column,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence,
                "label": f"{rel.source_column} → {rel.target_column}",
            }
        )

    schema_type = classify_schema_type(tables, relationships)

    return RelationshipGraph(
        nodes=nodes,
        edges=edges,
        schema_type=schema_type,
    )
