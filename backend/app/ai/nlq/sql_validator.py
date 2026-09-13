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
    """Validates SQL queries for safety."""

    def __init__(self, allow_writes: bool = False) -> None:
        self.allow_writes = allow_writes

    def validate(self, sql: str) -> str:
        """Validate SQL and return cleaned version. Raises SQLValidationError on failure."""
        if not sql or not sql.strip():
            raise SQLValidationError("Empty SQL query", "EMPTY_QUERY")

        cleaned = sql.strip().rstrip(";").strip()

        if not self.allow_writes:
            self._check_read_only(cleaned)

        self._check_injection(cleaned)
        self._check_length(cleaned)

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
