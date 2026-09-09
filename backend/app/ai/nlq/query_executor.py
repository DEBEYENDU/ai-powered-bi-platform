"""Query executor - safely executes validated SQL against the database."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.ai.nlq.sql_validator import SQLValidationError, SQLValidator


class QueryExecutor:
    """Executes validated SQL queries against the database."""

    def __init__(self, engine: Engine, timeout_seconds: int = 30, max_rows: int = 1000) -> None:
        self.engine = engine
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows
        self.validator = SQLValidator(allow_writes=False)

    def execute(self, sql: str) -> dict[str, Any]:
        """Validate and execute SQL, returning structured results."""
        cleaned_sql = self.validator.validate(sql)
        cleaned_sql = self._apply_row_limit(cleaned_sql)

        t0 = time.time()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(cleaned_sql))
                elapsed_ms = round((time.time() - t0) * 1000, 2)

                if result.returns_rows:
                    columns = list(result.keys())
                    rows = [
                        dict(zip(columns, row, strict=False))
                        for row in result.fetchmany(self.max_rows)
                    ]
                    row_count = len(rows)
                    truncated = row_count >= self.max_rows
                else:
                    columns = []
                    rows = []
                    row_count = 0
                    truncated = False

                return {
                    "success": True,
                    "sql": cleaned_sql,
                    "columns": columns,
                    "rows": rows,
                    "row_count": row_count,
                    "truncated": truncated,
                    "execution_time_ms": elapsed_ms,
                }
        except SQLValidationError:
            raise
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            return {
                "success": False,
                "sql": cleaned_sql,
                "error": str(exc),
                "execution_time_ms": elapsed_ms,
            }

    def _apply_row_limit(self, sql: str) -> str:
        upper = sql.upper().rstrip()
        if "LIMIT" not in upper:
            sql = f"{sql.rstrip()} LIMIT {self.max_rows}"
        return sql
