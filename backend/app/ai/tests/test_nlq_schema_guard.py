"""Ask Your Data (NLQ) schema-aware SQL generation regression tests.

Covers the reported failure: `what is this dataset about` generated SQL with a
nonexistent `ur.resource_id` column, surfacing a raw psycopg UndefinedColumn
error. Generated SQL must now be validated against the real schema, get one
bounded repair attempt, and fail with a safe message instead of a PostgreSQL
exception.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.ai.nlq.sql_validator import SQLValidationError, SQLValidator
from app.core.security import create_access_token
from app.main import app

ORG = str(uuid.uuid4())
OTHER_ORG = str(uuid.uuid4())
USER = str(uuid.uuid4())

CSV_BYTES = (
    b"product,region,sales\n"
    b"Widget,East,400\n"
    b"Widget,West,300\n"
    b"Gadget,East,200\n"
    b"Gizmo,North,100\n"
)

_uploaded: list[str] = []


def _auth(org: str = ORG) -> dict[str, str]:
    token = create_access_token({"sub": USER, "organization_id": org})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    from pathlib import Path

    from app.ai.data_engineering.models import DatasetRecord
    from app.core.config import get_settings
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        for did in _uploaded:
            rec = db.get(DatasetRecord, uuid.UUID(did))
            if rec is not None:
                db.delete(rec)
        db.commit()
    finally:
        db.close()
    root = Path(get_settings().storage_path)
    for did in _uploaded:
        for sub in ("de_versions", "de_datasets"):
            for path in (root / sub).glob(f"{did}*"):
                path.unlink(missing_ok=True)


def _real_schema() -> dict[str, set[str]]:
    from app.db.session import get_engine

    from app.ai.nlq.schema_explorer import SchemaExplorer

    schema = SchemaExplorer(get_engine()).get_schema()
    return {
        name: {c["name"].lower() for c in info.get("columns", [])}
        for name, info in schema["tables"].items()
    }


class TestSchemaAwareValidator:
    def test_hallucinated_column_is_rejected(self):
        """The exact reported failure: usage_records has NO resource_id."""
        validator = SQLValidator(schema=_real_schema())
        sql = (
            "SELECT d.name FROM usage_records ur "
            "JOIN datasets d ON ur.resource_id = d.id "
            "WHERE ur.resource_type = 'dataset'"
        )
        with pytest.raises(SQLValidationError, match="resource_id"):
            validator.validate(sql)

    def test_hallucinated_table_is_rejected(self):
        validator = SQLValidator(schema=_real_schema())
        with pytest.raises(SQLValidationError, match="does not exist"):
            validator.validate("SELECT * FROM not_a_real_table")

    def test_valid_sql_passes(self):
        validator = SQLValidator(schema=_real_schema())
        sql = "SELECT name, row_count FROM de_datasets WHERE organization_id = 'x'"
        assert validator.validate(sql) == sql.rstrip(";").strip()

    def test_write_operations_are_rejected(self):
        validator = SQLValidator(schema=_real_schema())
        for bad in (
            "INSERT INTO datasets (name) VALUES ('x')",
            "UPDATE datasets SET name = 'x'",
            "DELETE FROM datasets",
            "DROP TABLE datasets",
            "TRUNCATE datasets",
        ):
            with pytest.raises(SQLValidationError):
                validator.validate(bad)

    def test_tenant_scoped_table_requires_organization_filter(self):
        schema = _real_schema()
        validator = SQLValidator(schema=schema, organization_id=ORG)
        with pytest.raises(SQLValidationError, match="organization_id"):
            validator.validate("SELECT name, row_count FROM de_datasets")
        # With the filter it passes
        validator.validate(f"SELECT name, row_count FROM de_datasets WHERE organization_id = '{ORG}'")

    def test_unscoped_platform_tables_stay_allowed(self):
        validator = SQLValidator(schema=_real_schema(), organization_id=ORG)
        assert validator.validate("SELECT COUNT(*) FROM organizations")

    def test_query_with_org_id_of_another_org_is_scoped_to_caller(self):
        """The validator enforces the CALLER's org id, not the LLM's text."""
        validator = SQLValidator(schema=_real_schema(), organization_id=ORG)
        with pytest.raises(SQLValidationError, match="organization_id"):
            validator.validate(
                f"SELECT name FROM de_datasets WHERE organization_id = '{OTHER_ORG}'"
            )


class TestNLQEndToEnd:
    def test_what_is_this_dataset_about(self, client: TestClient):
        """The exact reported question, against the real LLM and schema."""
        resp = client.post(
            "/api/v1/ai/de/upload",
            files={"file": ("sales.csv", CSV_BYTES, "text/csv")},
            headers=_auth(),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True, body
        _uploaded.append(body["dataset_id"])

        r = client.post(
            "/api/v1/ai/query",
            json={"question": "what is this dataset about", "include_chart": False},
            headers=_auth(),
        )
        assert r.status_code == 200, r.text
        b = r.json()
        # Either it answered from the real schema (de_datasets) or it failed
        # with a SAFE, understandable error — never a raw psycopg exception.
        raw = str(b)
        assert "psycopg" not in raw
        assert "UndefinedColumn" not in raw
        assert "traceback" not in raw.lower()
        if b.get("success"):
            sql = str(b.get("sql", "")).lower()
            assert "de_datasets" in sql, "dataset questions must use the real table"
            # Tenant scope enforced on the executed SQL
            assert "organization_id" in sql, b
        else:
            assert b.get("error"), b
            assert "column" in str(b.get("error", "")).lower() or "rephrase" in str(
                b.get("error", "")
            ).lower()

    def test_hallucinated_schema_never_reaches_the_user(self, client: TestClient):
        """Simulate a model that generates the exact broken SQL from the report:
        the validator must reject it and the response must carry a safe error."""
        from unittest.mock import patch

        broken_sql = (
            "SELECT d.name FROM usage_records ur "
            "JOIN datasets d ON ur.resource_id = d.id "
            "WHERE ur.resource_type = 'dataset'"
        )

        class BrokenGenerator:
            def __init__(self, *a: object, **k: object) -> None:
                pass

            async def generate(self, **kwargs: object) -> dict:
                return {"sql": broken_sql, "explanation": "broken"}

        from app.ai.nlq.nl2sql_service import NL2SQLService
        from app.db.session import get_engine

        service = NL2SQLService(engine=get_engine(), organization_id=ORG)
        with patch.object(service, "generator", BrokenGenerator()):
            import asyncio

            result = asyncio.run(
                service.query("what is this dataset about", include_chart=False)
            )
        assert result["success"] is False
        assert "psycopg" not in str(result)
        assert result["error"], result
        assert "resource_id" in str(result["error"]) or "rephrase" in str(result["error"])
