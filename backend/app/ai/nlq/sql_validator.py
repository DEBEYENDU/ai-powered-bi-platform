"""SQL validator - ensures only safe SELECT statements are executed."""

from __future__ import annotations

import re


class SQLValidationError(Exception):
    """Raised when SQL fails safety validation."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message)
        self.code = code


# Patterns that indicate write/destructive operations.
_BLOCKED_PATTERNS: list[tuple[str, str]] = [
    (r"\bINSERT\s+INTO\b", "INSERT is not allowed"),
    (r"\bUPDATE\s+\w+\s+SET\b", "UPDATE is not allowed"),
    (r"\bDELETE\s+FROM\b", "DELETE is not allowed"),
    (r"\bDROP\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b", "DROP is not allowed"),
    (r"\bALTER\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b", "ALTER is not allowed"),
    (r"\bCREATE\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA|ROLE)\b", "CREATE is not allowed"),
    (r"\bTRUNCATE\b", "TRUNCATE is not allowed"),
    (r"\bGRANT\b", "GRANT is not allowed"),
    (r"\bREVOKE\b", "REVOKE is not allowed"),
    (r"\bEXEC(UTE)?\b", "EXEC is not allowed"),
    (r"\bINTO\s+OUTFILE\b", "INTO OUTFILE is not allowed"),
    (r"\bLOAD\s+DATA\b", "LOAD DATA is not allowed"),
    (r"\bINTO\s+DUMPFILE\b", "INTO DUMPFILE is not allowed"),
]

# Patterns for multi-statement injection.
_MULTI_STATEMENT_PATTERNS = [
    r";\s*\w",  # semicolon followed by another statement
    r"--\s*\n",  # SQL comment followed by newline (possible injection)
]


class SQLValidator:
    """Validates SQL queries for safety, schema existence, and tenant scope."""

    def __init__(
        self,
        allow_writes: bool = False,
        schema: dict[str, set[str]] | None = None,
        organization_id: str | None = None,
    ) -> None:
        """``schema`` maps real table names to their column names; when given,
        generated SQL is rejected before execution if it references tables or
        columns that do not exist (LLM hallucinations used to surface as raw
        psycopg errors). ``organization_id`` enables the tenant-scope check."""
        self.allow_writes = allow_writes
        self.schema = schema or {}
        self.organization_id = organization_id

    def validate(self, sql: str) -> str:
        """Validate SQL and return cleaned version. Raises SQLValidationError on failure."""
        if not sql or not sql.strip():
            raise SQLValidationError("Empty SQL query", "EMPTY_QUERY")

        cleaned = sql.strip().rstrip(";").strip()

        if not self.allow_writes:
            self._check_read_only(cleaned)

        self._check_injection(cleaned)
        self._check_length(cleaned)
        self._check_schema(cleaned)

        return cleaned

    def _check_read_only(self, sql: str) -> None:
        upper = sql.upper()
        for pattern, message in _BLOCKED_PATTERNS:
            if re.search(pattern, upper, re.IGNORECASE):
                raise SQLValidationError(message, "WRITE_NOT_ALLOWED")

        if not re.match(r"^\s*SELECT\b", upper):
            raise SQLValidationError("Only SELECT statements are allowed", "SELECT_ONLY")

    def _check_injection(self, sql: str) -> None:
        for pattern in _MULTI_STATEMENT_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                raise SQLValidationError(
                    "Multi-statement queries are not allowed", "MULTI_STATEMENT"
                )

        dangerous_functions = [
            "LOAD_FILE",
            "INTO_OUTFILE",
            "INTO_DUMPFILE",
            "BENCHMARK",
            "SLEEP(",
            "WAITFOR",
            "DBMS_PIPE",
            "UTL_HTTP",
        ]
        upper = sql.upper()
        for func in dangerous_functions:
            if func in upper:
                raise SQLValidationError(f"Function {func} is not allowed", "DANGEROUS_FUNCTION")

    def _check_length(self, sql: str) -> None:
        if len(sql) > 10000:
            raise SQLValidationError(
                "SQL query exceeds maximum length (10000 chars)", "QUERY_TOO_LONG"
            )

    # Tables whose rows belong to a single organization. AI-generated SQL
    # touching them must filter by organization_id — enforced here, not left
    # to the LLM.
    TENANT_SCOPED_TABLES = frozenset(
        {
            "datasets",
            "de_datasets",
            "de_dataset_versions",
            "de_pipelines",
            "conversations",
            "ai_messages",
            "reports",
            "dashboards",
            "knowledge_documents",
            "knowledge_collections",
            "usage_records",
            "tenant_api_keys",
            "users",
        }
    )

    _TABLE_REF = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+AS\s+)?(\s*[a-zA-Z_][a-zA-Z0-9_]*)?", re.IGNORECASE)
    _QUALIFIED_COL = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b")
    _SQL_KEYWORDS = frozenset(
        {
            "where", "order", "group", "limit", "on", "inner", "left", "right",
            "full", "cross", "join", "union", "select", "set", "having",
            "offset", "as", "natural", "using", "values", "asc", "desc",
        }
    )

    def _check_schema(self, sql: str) -> None:
        if not self.schema:
            return

        aliases: dict[str, str] = {}
        for match in self._TABLE_REF.finditer(sql):
            table = match.group(1).lower()
            alias = (match.group(2) or "").strip().lower()
            if table not in self.schema:
                raise SQLValidationError(
                    f"Table '{table}' does not exist in the database", "UNKNOWN_TABLE"
                )
            if alias and alias not in self._SQL_KEYWORDS:
                aliases[alias] = table
            aliases.setdefault(table, table)

        for alias, column in self._QUALIFIED_COL.findall(sql):
            table = aliases.get(alias.lower())
            if table is None:
                # Subquery/CTE alias — cannot be verified statically.
                continue
            if column.lower() not in self.schema[table]:
                raise SQLValidationError(
                    f"Column '{alias}.{column}' does not exist on table '{table}'",
                    "UNKNOWN_COLUMN",
                )

        # Tenant scope: tenant-scoped tables require the CALLER's organization
        # filter. String literals are stripped first so mentions inside '%…%'
        # do not count as table references; the caller's org id must appear in
        # the SQL itself (the generator is given it in the prompt), so a query
        # scoped to another tenant is rejected here — not just filtered later.
        if self.organization_id:
            sql_lower = re.sub(r"'[^']*'", "", sql.lower())
            touches_tenant_data = any(
                re.search(rf"\b{re.escape(t)}\b", sql_lower)
                for t in self.TENANT_SCOPED_TABLES
            )
            org_in_sql = self.organization_id.lower() in sql.lower()
            if touches_tenant_data and not org_in_sql:
                raise SQLValidationError(
                    "Queries on tenant data must filter by your organization_id",
                    "TENANT_SCOPE_REQUIRED",
                )
