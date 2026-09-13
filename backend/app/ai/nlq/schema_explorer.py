"""Schema explorer - introspects the database and builds a structured representation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.engine import Engine


class SchemaExplorer:
    """Introspects the database and produces a schema description for the LLM."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._cache: dict[str, Any] | None = None

    def get_schema(self, force_refresh: bool = False) -> dict[str, Any]:
        """Return full schema as a structured dict (cached after first call)."""
        if self._cache is not None and not force_refresh:
            return self._cache

        inspector = sa_inspect(self.engine)
        schema: dict[str, Any] = {
            "database": str(self.engine.url.database),
            "tables": {},
            "relationships": [],
        }

        table_names = inspector.get_table_names()
        for table_name in sorted(table_names):
            table_info = self._explore_table(inspector, table_name)
            schema["tables"][table_name] = table_info

        schema["relationships"] = self._extract_relationships(inspector, table_names)
        self._cache = schema
        return schema

    def _explore_table(self, inspector: Any, table_name: str) -> dict[str, Any]:
        columns = inspector.get_columns(table_name)
        pk_cols = inspector.get_pk_constraint(table_name)
        indexes = inspector.get_indexes(table_name)

        col_list: list[dict[str, Any]] = []
        for col in columns:
            col_info: dict[str, Any] = {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
            }
            if col.get("default") is not None:
                col_info["default"] = str(col["default"])
            col_list.append(col_info)

        pk_columns = pk_cols.get("constrained_columns", []) if pk_cols else []

        return {
            "columns": col_list,
            "primary_key": pk_columns,
            "indexes": [
                {"name": idx.get("name", ""), "columns": idx.get("column_names", [])}
                for idx in indexes
            ],
            "row_count_estimate": self._estimate_row_count(table_name),
        }

    def _estimate_row_count(self, table_name: str) -> int | None:
        try:
            with self.engine.connect() as conn:
                # S608: table_name comes from inspector, not user input
                result = conn.execute(
                    __import__("sqlalchemy").text(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
                )
                return result.scalar()
        except Exception:  # noqa: BLE001
            return None

    def _extract_relationships(
        self, inspector: Any, table_names: list[str]
    ) -> list[dict[str, Any]]:
        relationships: list[dict[str, Any]] = []
        for table_name in table_names:
            fks = inspector.get_foreign_keys(table_name)
            for fk in fks:
                relationships.append(
                    {
                        "from_table": table_name,
                        "from_columns": fk.get("constrained_columns", []),
                        "to_table": fk.get("referred_table", ""),
                        "to_columns": fk.get("referred_columns", []),
                    }
                )
        return relationships

    def get_schema_text(self) -> str:
        """Return a human-readable schema text suitable for LLM prompts."""
        schema = self.get_schema()
        lines: list[str] = []

        for table_name, table_info in schema["tables"].items():
            lines.append(f"\nTable: {table_name}")
            if table_info["primary_key"]:
                lines.append(f"  Primary Key: {', '.join(table_info['primary_key'])}")
            lines.append("  Columns:")
            for col in table_info["columns"]:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                lines.append(f"    - {col['name']} ({col['type']}) {nullable}")

        if schema["relationships"]:
            lines.append("\nForeign Key Relationships:")
            for rel in schema["relationships"]:
                from_cols = ", ".join(rel["from_columns"])
                to_cols = ", ".join(rel["to_columns"])
                lines.append(f"  {rel['from_table']}.{from_cols} -> {rel['to_table']}.{to_cols}")

        return "\n".join(lines)
