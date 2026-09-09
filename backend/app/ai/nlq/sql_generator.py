"""SQL generator - uses LLM to convert natural language to SQL."""

from __future__ import annotations

from typing import Any

from app.ai.providers.base import ChatMessage, LLMProvider
from app.ai.providers.registry import get_provider

NL2SQL_SYSTEM_PROMPT = """\
You are an expert SQL developer for a PostgreSQL database.
You convert natural language questions into precise, efficient SQL queries.

RULES:
1. Generate ONLY a single SELECT statement. Never use INSERT, UPDATE, DELETE, DROP, ALTER, or CREATE.
2. Use PostgreSQL syntax (e.g., ILIKE for case-insensitive LIKE, NOW() for current time).
3. Use proper JOINs when data from multiple tables is needed.
4. Always use table aliases for clarity (e.g., u for users, o for organizations).
5. Return meaningful column aliases (e.g., AS total_revenue, AS user_count).
6. For aggregations, always GROUP BY the non-aggregated columns.
7. Use LIMIT to cap results at 100 rows unless the user asks for more.
8. Use ORDER BY to sort results logically (e.g., by date, by count descending).
9. For date filtering, use PostgreSQL date functions (DATE_TRUNC, INTERVAL, etc.).
10. Never fabricate table or column names. Only use names from the schema provided.
11. Wrap the SQL in ```sql code fences.
12. After the SQL, provide a brief explanation of what the query does.

RESPONSE FORMAT:
```sql
YOUR SQL QUERY HERE
```

EXPLANATION: Brief explanation of the query logic.
"""

EXPLAIN_SYSTEM_PROMPT = """\
You are an expert SQL analyst. Explain the given SQL query in plain language.
Break down what each part of the query does.
Describe what the results would look like.
Suggest improvements if any.
"""


class SQLGenerator:
    """Generates SQL from natural language using an LLM provider."""

    def __init__(self, provider: LLMProvider | None = None, model: str = "") -> None:
        self.provider = provider or get_provider()
        self.model = model or "gpt-4o-mini"

    async def generate(
        self,
        question: str,
        schema_text: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Generate SQL from a natural language question."""
        messages = [
            ChatMessage(role="system", content=NL2SQL_SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=(
                    f"DATABASE SCHEMA:\n{schema_text}\n\n"
                    f"QUESTION: {question}\n\n"
                    "Generate the SQL query and explanation."
                ),
            ),
        ]

        response = await self.provider.chat(
            messages, model=self.model, temperature=temperature, max_tokens=max_tokens
        )

        return self._parse_response(response.content)

    async def explain(
        self,
        sql: str,
        schema_text: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Explain what a SQL query does."""
        messages = [
            ChatMessage(role="system", content=EXPLAIN_SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=(
                    f"DATABASE SCHEMA:\n{schema_text}\n\n"
                    f"SQL QUERY:\n{sql}\n\n"
                    "Explain this query."
                ),
            ),
        ]

        response = await self.provider.chat(
            messages, model=self.model, temperature=temperature, max_tokens=max_tokens
        )
        return response.content

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse LLM response into SQL and explanation."""
        sql = ""
        explanation = ""

        import re

        sql_match = re.search(r"```sql\s*\n(.*?)```", content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            lines = content.strip().split("\n")
            sql_lines: list[str] = []
            for line in lines:
                stripped = line.strip()
                if stripped.upper().startswith("EXPLANATION:"):
                    explanation = stripped[len("EXPLANATION:") :].strip()
                    break
                if stripped and not stripped.startswith("```"):
                    sql_lines.append(stripped)
            sql = " ".join(sql_lines)

        if not explanation:
            expl_match = re.search(
                r"EXPLANATION:\s*(.*)", content, re.IGNORECASE | re.DOTALL
            )
            if expl_match:
                explanation = expl_match.group(1).strip()

        return {"sql": sql, "explanation": explanation}
