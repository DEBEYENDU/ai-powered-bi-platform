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
    ) -> None:
        self.engine = engine
        self.provider = provider or get_provider()
        self.model = model
        self.explorer = SchemaExplorer(engine)
        self.generator = SQLGenerator(provider=self.provider, model=model)
        self.validator = SQLValidator(allow_writes=False)
        self.executor = QueryExecutor(engine)

    def get_schema(self, force_refresh: bool = False) -> dict[str, Any]:
        """Get full database schema."""
        return self.explorer.get_schema(force_refresh=force_refresh)

    def get_schema_text(self) -> str:
        """Get schema as text for LLM prompts."""
        return self.explorer.get_schema_text()

    async def query(
        self,
        question: str,
        include_chart: bool = True,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Full pipeline: question -> SQL -> validate -> execute -> chart recommendation."""
        schema_text = self.get_schema_text()

        generated = await self.generator.generate(
            question=question,
            schema_text=schema_text,
            temperature=temperature,
        )

        sql = generated["sql"]
        explanation = generated["explanation"]

        if not sql:
            return {
                "success": False,
                "question": question,
                "sql": "",
                "error": "Could not generate SQL from the question.",
                "explanation": explanation,
            }

        try:
            validated_sql = self.validator.validate(sql)
        except SQLValidationError as exc:
            return {
                "success": False,
                "question": question,
                "sql": sql,
                "error": f"Generated SQL failed validation: {exc}",
                "explanation": explanation,
            }

        result = self.executor.execute(validated_sql)

        chart_recommendation = self._recommend_chart(result) if include_chart else None

        return {
            "success": result["success"],
            "question": question,
            "sql": result.get("sql", validated_sql),
            "columns": result.get("columns", []),
            "rows": result.get("rows", []),
            "row_count": result.get("row_count", 0),
            "truncated": result.get("truncated", False),
            "execution_time_ms": result.get("execution_time_ms", 0),
            "explanation": explanation,
            "chart_recommendation": chart_recommendation,
            "error": result.get("error"),
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
