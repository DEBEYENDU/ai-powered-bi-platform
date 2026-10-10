"""NL2SQL service - orchestrates schema exploration, SQL generation, validation, and execution."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine

from app.ai.nlq.query_executor import QueryExecutor
from app.ai.nlq.schema_explorer import SchemaExplorer
from app.ai.nlq.sql_generator import SQLGenerator
from app.ai.nlq.sql_validator import SQLValidationError, SQLValidator
from app.ai.providers.base import LLMProvider
from app.ai.providers.registry import get_provider


class NL2SQLService:
    """Complete Natural Language to SQL pipeline."""

    def __init__(
        self,
        engine: Engine,
        provider: LLMProvider | None = None,
        model: str = "",
        organization_id: str | None = None,
    ) -> None:
        self.engine = engine
        self.provider = provider or get_provider()
        self.model = model
        self.organization_id = organization_id
        self.explorer = SchemaExplorer(engine)
        self.generator = SQLGenerator(provider=self.provider, model=model)
        self.executor = QueryExecutor(engine)
        self._schema_map: dict[str, set[str]] | None = None

    def get_schema(self, force_refresh: bool = False) -> dict[str, Any]:
        """Get full database schema."""
        return self.explorer.get_schema(force_refresh=force_refresh)

    def get_schema_text(self) -> str:
        """Get schema as text for LLM prompts."""
        return self.explorer.get_schema_text()

    def _schema_columns(self) -> dict[str, set[str]]:
        """Real tables -> column names, used to validate generated SQL."""
        if self._schema_map is None:
            schema = self.get_schema()
            self._schema_map = {
                name: {c["name"].lower() for c in info.get("columns", [])}
                for name, info in schema.get("tables", {}).items()
            }
        return self._schema_map

    def _validator(self) -> SQLValidator:
        return SQLValidator(
            allow_writes=False,
            schema=self._schema_columns(),
            organization_id=self.organization_id,
        )

    @staticmethod
    def _safe_db_error(error_text: str) -> str:
        """Human-readable message for a failed execution — no internals."""
        low = error_text.lower()
        if "undefinedcolumn" in low or ("does not exist" in low and "column" in low):
            return (
                "The generated query referenced a column that does not exist "
                "in the database. Please rephrase the question."
            )
        if "undefinedtable" in low:
            return (
                "The generated query referenced a table that does not exist "
                "in the database. Please rephrase the question."
            )
        if "syntax error" in low:
            return "The generated SQL was invalid and could not be executed. Please rephrase the question."
        if "timeout" in low or "canceling statement" in low:
            return "The query took too long and was cancelled. Try a narrower question."
        return "The query could not be executed. Please rephrase the question."

    async def query(
        self,
        question: str,
        include_chart: bool = True,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Full pipeline: question -> SQL -> validate -> execute -> chart recommendation.

        Schema-invalid or failed SQL gets ONE bounded repair attempt (the
        validation/execution error is fed back to the generator); a second
        failure returns a safe, understandable error instead of a raw
        PostgreSQL exception.
        """
        validator = self._validator()
        schema_text = self.get_schema_text()

        repair_error = ""
        last_sql = ""
        last_error = ""
        explanation = ""

        for _ in range(2):  # bounded: 1 initial + 1 repair
            generated = await self.generator.generate(
                question=question,
                schema_text=schema_text,
                temperature=temperature,
                repair_error=repair_error,
                organization_id=self.organization_id,
            )

            sql = generated["sql"]
            explanation = generated["explanation"]
            last_sql = sql

            if not sql:
                last_error = "Could not generate SQL from the question."
                repair_error = last_error
                continue

            try:
                validated_sql = validator.validate(sql)
            except SQLValidationError as exc:
                last_error = self._safe_db_error(str(exc))
                repair_error = (
                    f"Your previous SQL was rejected: {exc}. "
                    "Regenerate it using ONLY tables and columns from the schema provided."
                )
                continue

            result = self.executor.execute(validated_sql)
            if result.get("success"):
                chart_recommendation = self._recommend_chart(result) if include_chart else None
                return {
                    "success": True,
                    "question": question,
                    "sql": result.get("sql", validated_sql),
                    "columns": result.get("columns", []),
                    "rows": result.get("rows", []),
                    "row_count": result.get("row_count", 0),
                    "truncated": result.get("truncated", False),
                    "execution_time_ms": result.get("execution_time_ms", 0),
                    "explanation": explanation,
                    "chart_recommendation": chart_recommendation,
                    "error": None,
                }

            # Execution failed: repair once for schema-level mistakes.
            last_error = self._safe_db_error(str(result.get("error", "")))
            raw_error = str(result.get("error", ""))
            repairable = any(
                kw in raw_error.lower()
                for kw in ("undefinedcolumn", "undefinedtable", "does not exist", "syntax error")
            )
            if not repairable:
                break
            repair_error = (
                f"Your previous SQL failed to execute: {raw_error[:300]}. "
                "Regenerate it using ONLY tables and columns from the schema provided."
            )

        return {
            "success": False,
            "question": question,
            "sql": last_sql,
            "error": last_error or "Could not generate a valid query.",
            "explanation": explanation if last_sql else "",
        }

    async def explain_sql(
        self,
        sql: str,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Explain a SQL query."""
        schema_text = self.get_schema_text()

        try:
            validated_sql = self.validator.validate(sql)
        except SQLValidationError as exc:
            return {"sql": sql, "explanation": "", "error": str(exc)}

        explanation = await self.generator.explain(
            sql=validated_sql,
            schema_text=schema_text,
            temperature=temperature,
        )

        return {
            "sql": validated_sql,
            "explanation": explanation,
            "error": None,
        }

    def _recommend_chart(self, result: dict[str, Any]) -> dict[str, Any] | None:
        """Recommend a chart type based on the query results."""
        if not result.get("success") or not result.get("columns"):
            return None

        columns = result["columns"]
        rows = result.get("rows", [])

        if len(rows) < 2:
            return None

        has_date = any(
            any(
                kw in col.lower()
                for kw in ["date", "time", "created", "updated", "month", "year", "day"]
            )
            for col in columns
        )

        numeric_cols = [
            col
            for col in columns
            if rows and any(isinstance(r.get(col), (int, float)) for r in rows[:10])
        ]

        categorical_cols = [col for col in columns if col not in numeric_cols]

        if len(rows) > 20 and has_date and numeric_cols:
            return {
                "type": "line",
                "x_axis": next(
                    (
                        c
                        for c in columns
                        if any(kw in c.lower() for kw in ["date", "time", "created"])
                    ),
                    columns[0],
                ),
                "y_axis": numeric_cols[0],
                "reason": "Time series data detected with numeric values.",
            }

        if categorical_cols and numeric_cols and len(rows) <= 20:
            return {
                "type": "bar",
                "x_axis": categorical_cols[0],
                "y_axis": numeric_cols[0],
                "reason": "Categorical data with numeric values.",
            }

        if len(numeric_cols) >= 2:
            return {
                "type": "scatter",
                "x_axis": numeric_cols[0],
                "y_axis": numeric_cols[1],
                "reason": "Two numeric columns detected.",
            }

        if len(rows) <= 8 and numeric_cols:
            return {
                "type": "pie",
                "x_axis": categorical_cols[0] if categorical_cols else columns[0],
                "y_axis": numeric_cols[0],
                "reason": "Small dataset with categorical and numeric data.",
            }

        if numeric_cols:
            return {
                "type": "bar",
                "x_axis": columns[0],
                "y_axis": numeric_cols[0],
                "reason": "Default bar chart for tabular data.",
            }

        return None
