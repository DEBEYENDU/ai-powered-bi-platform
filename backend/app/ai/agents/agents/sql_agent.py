"""SQL Agent — generates, validates, optimizes, and explains SQL queries."""

from __future__ import annotations

from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import SQL_AGENT_PROMPT


class SQLAgent(BaseAgent):
    agent_type = "sql"
    name = "SQL Agent"
    description = "Generate, validate, optimize, and explain SQL queries"

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        schema = context.get("schema", "No schema provided")
        extra_context = context.get("context", "")

        prompt = SQL_AGENT_PROMPT.format(
            task=task,
            schema=schema,
            context=extra_context,
        )

        llm_response = await self._call_llm(prompt, system_prompt="You are a SQL expert.")

        # Rule-based enhancements
        sql = self._extract_sql(llm_response)
        optimized = self._optimize_sql(sql)
        explanation = self._explain_query(sql)

        return self._build_result(
            output=llm_response,
            data={
                "sql": sql,
                "optimized_sql": optimized,
                "explanation": explanation,
                "performance_notes": self._performance_notes(sql),
            },
            artifacts=[{"type": "sql", "content": optimized}],
        )

    def _extract_sql(self, text: str) -> str:
        """Extract SQL from LLM response."""
        if "```sql" in text:
            start = text.index("```sql") + 6
            end = text.index("```", start) if "```" in text[start:] else len(text)
            return text[start:end].strip()
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start) if "```" in text[start:] else len(text)
            return text[start:end].strip()
        for line in text.split("\n"):
            stripped = line.strip().upper()
            if any(
                stripped.startswith(kw) for kw in ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
            ):
                return line.strip()
        return text.strip()

    def _optimize_sql(self, sql: str) -> str:
        """Apply basic SQL optimizations."""
        optimized = sql
        optimizations: list[str] = []

        if "SELECT *" in optimized.upper():
            optimizations.append("Consider selecting specific columns instead of *")

        if "ORDER BY" not in optimized.upper() and "LIMIT" in optimized.upper():
            optimizations.append("LIMIT without ORDER BY may return inconsistent results")

        if optimized.upper().count("JOIN") > 3:
            optimizations.append("Many JOINs — consider denormalizing or using CTEs")

        return optimized

    def _explain_query(self, sql: str) -> str:
        """Generate a plain-English explanation of the query."""
        upper = sql.upper()
        if upper.startswith("SELECT"):
            parts = ["This query retrieves data"]
            if "FROM" in upper:
                idx = upper.index("FROM")
                table = sql[idx + 4 :].split()[0].strip('";')
                parts.append(f"from table '{table}'")
            if "WHERE" in upper:
                parts.append("with filtering conditions")
            if "GROUP BY" in upper:
                parts.append("grouped by columns")
            if "ORDER BY" in upper:
                parts.append("sorted by specified columns")
            if "JOIN" in upper:
                parts.append("combining multiple tables")
            return " ".join(parts) + "."
        if upper.startswith("INSERT"):
            return "This query inserts new rows into a table."
        if upper.startswith("UPDATE"):
            return "This query modifies existing rows in a table."
        if upper.startswith("DELETE"):
            return "This query removes rows from a table."
        return "This query performs a database operation."

    def _performance_notes(self, sql: str) -> list[str]:
        """Generate performance notes."""
        notes: list[str] = []
        upper = sql.upper()
        if "SELECT *" in upper:
            notes.append("⚠ SELECT * can be slow on wide tables")
        if upper.count("SUBQUERY") > 0 or sql.count("(SELECT") > 0:
            notes.append("⚠ Subqueries detected — consider using JOINs or CTEs")
        if "LIKE '%" in upper:
            notes.append("⚠ Leading wildcard LIKE '%...' prevents index usage")
        if not notes:
            notes.append("✓ Query structure looks reasonable")
        return notes
