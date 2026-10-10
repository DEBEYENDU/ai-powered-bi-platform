"""Upload → list → tenant-scoped access regression tests.

These run against the real dev database and storage directory: an upload must
create a ``de_datasets`` record, must show up in ``GET /ai/de/datasets`` for
its own organization only, and must be refused to every other tenant.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token
from app.main import app

# 4 rows, 3 products, sales total 1000, average 250 (computed in the test,
# never hardcoded as an expected literal in the assertions below).
CSV_BYTES = (
    b"product,region,sales\n"
    b"Widget,East,400\n"
    b"Widget,West,300\n"
    b"Gadget,East,200\n"
    b"Gizmo,North,100\n"
)
CSV_ROWS = 4
CSV_SALES_TOTAL = 1000

ORG_A = str(uuid.uuid4())
ORG_B = str(uuid.uuid4())
USER = str(uuid.uuid4())

_uploaded: list[str] = []


def _auth(org: str) -> dict[str, str]:
    token = create_access_token({"sub": USER, "organization_id": org})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def uploaded(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/ai/de/upload",
        files={"file": ("sales.csv", CSV_BYTES, "text/csv")},
        headers=_auth(ORG_A),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True, body
    _uploaded.append(body["dataset_id"])
    return body


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    from app.ai.data_engineering.models import DatasetRecord
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
    root = Path(get_settings().storage_path) / "de_versions"
    for did in _uploaded:
        for path in list(root.glob(f"{did}*")):
            path.unlink(missing_ok=True)
    raw_root = Path(get_settings().storage_path) / "de_datasets"
    for did in _uploaded:
        for path in list(raw_root.glob(f"{did}*")):
            path.unlink(missing_ok=True)


class TestUploadAndList:
    def test_upload_reports_counts_and_status(self, uploaded: dict):
        assert uploaded["row_count"] == CSV_ROWS
        assert uploaded["column_count"] == 3
        assert uploaded["status"] == "ready"
        assert uploaded["file_size"] == len(CSV_BYTES)
        assert uploaded["error"] is None

    def test_uploaded_dataset_is_listed(self, client: TestClient, uploaded: dict):
        resp = client.get("/api/v1/ai/de/datasets", headers=_auth(ORG_A))
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] >= 1
        match = [d for d in body["datasets"] if d["dataset_id"] == uploaded["dataset_id"]]
        assert match, "uploaded dataset missing from GET /ai/de/datasets"
        row = match[0]
        assert row["row_count"] == CSV_ROWS
        assert row["column_count"] == 3
        assert row["status"] == "ready"
        assert row["name"] == "sales.csv"

    def test_upload_of_header_only_csv_is_rejected(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/de/upload",
            files={"file": ("empty.csv", b"a,b,c\n", "text/csv")},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["error"]

    def test_upload_of_garbage_file_is_rejected(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/de/upload",
            files={"file": ("broken.csv", b"\x00\x01\x02 not,a,csv", "text/csv")},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["error"]

    def test_rejected_uploads_leave_no_files_behind(self, client: TestClient):
        def snapshot() -> set[str]:
            root = Path(get_settings().storage_path)
            names: set[str] = set()
            for sub in ("de_datasets", "de_versions"):
                names.update(p.name for p in (root / sub).glob("*"))
            return names

        before = snapshot()
        for filename, payload in (
            ("empty.csv", b"a,b,c\n"),
            ("broken.csv", b"\x00\x01\x02 binary"),
            ("nocols.csv", b""),
        ):
            resp = client.post(
                "/api/v1/ai/de/upload",
                files={"file": (filename, payload, "text/csv")},
                headers=_auth(ORG_A),
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is False, resp.text
        assert snapshot() == before, "rejected uploads must not leave files in storage"

    def test_upload_rejects_unsupported_file_type(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/de/upload",
            files={"file": ("report.exe", b"MZ fake binary", "application/octet-stream")},
            data={"source_type": "exe"},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "Unsupported file type" in (body.get("error") or "")

    def test_upload_enforces_size_limit(self, client: TestClient, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "data_max_upload_size", 100)
        big = b"product,region,sales\n" + b"Widget,East,400\n" * 20  # > 100 bytes
        assert len(big) > 100
        resp = client.post(
            "/api/v1/ai/de/upload",
            files={"file": ("big.csv", big, "text/csv")},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "upload limit" in (body.get("error") or "")


class TestTenantIsolation:
    def test_other_org_sees_empty_list(self, client: TestClient, uploaded: dict):
        resp = client.get("/api/v1/ai/de/datasets", headers=_auth(ORG_B))
        assert resp.status_code == 200
        ids = [d["dataset_id"] for d in resp.json()["datasets"]]
        assert uploaded["dataset_id"] not in ids

    def test_other_org_cannot_profile(self, client: TestClient, uploaded: dict):
        resp = client.post(
            "/api/v1/ai/de/profile",
            json={"dataset_id": uploaded["dataset_id"]},
            headers=_auth(ORG_B),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["error"] == "Dataset not found"

    def test_other_org_cannot_chat(self, client: TestClient, uploaded: dict):
        resp = client.post(
            "/api/v1/ai/de/chat",
            json={"dataset_id": uploaded["dataset_id"], "question": "total sales?"},
            headers=_auth(ORG_B),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["confidence"] == "low"
        assert "not found" in body["answer"].lower()

    def test_other_org_cannot_export(self, client: TestClient, uploaded: dict):
        resp = client.post(
            "/api/v1/ai/de/export",
            json={"dataset_id": uploaded["dataset_id"], "format": "csv"},
            headers=_auth(ORG_B),
        )
        assert resp.status_code == 404

    def test_unknown_org_cannot_list(self, client: TestClient):
        resp = client.get("/api/v1/ai/de/datasets")
        assert resp.status_code == 401


class TestDerivedDatasetAccess:
    def test_derived_id_resolves_through_base_record(self, uploaded: dict):
        from app.ai.data_engineering.services import dataset_store
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            derived = f"{uploaded['dataset_id']}_clean"
            assert dataset_store.owns_dataset(db, ORG_A, derived) is True
            assert dataset_store.owns_dataset(db, ORG_B, derived) is False
            assert dataset_store.owns_dataset(db, ORG_A, str(uuid.uuid4())) is False
            assert dataset_store.owns_dataset(db, ORG_A, "not-a-uuid") is False
        finally:
            db.close()


class TestProfileGrounding:
    def test_profile_reads_the_uploaded_rows(self, client: TestClient, uploaded: dict, monkeypatch):
        from app.ai.data_engineering.services import orchestrator

        async def _no_network(*args, **kwargs):
            return ["offline insight"]

        monkeypatch.setattr(orchestrator.ai_service, "get_dataset_insights", _no_network)
        resp = client.post(
            "/api/v1/ai/de/profile",
            json={"dataset_id": uploaded["dataset_id"]},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["row_count"] == CSV_ROWS
        assert body["column_count"] == 3

    def test_dataset_chat_prompt_carries_real_rows_and_aggregates(
        self, uploaded: dict, monkeypatch
    ):
        """The model must receive the actual data, not just column names."""
        import asyncio

        from app.ai.data_engineering.services import ai_service

        captured: dict = {}

        class _FakeLLM:
            async def chat_completion(self, messages, **kwargs):
                captured["messages"] = messages
                return "Total sales are 1000 across 4 rows."

        monkeypatch.setattr(ai_service, "_get_llm", lambda: _FakeLLM())

        from app.ai.data_engineering.schemas import DatasetChatRequest
        from app.ai.data_engineering.services import orchestrator

        result = asyncio.run(
            orchestrator.dataset_chat(
                DatasetChatRequest(dataset_id=uploaded["dataset_id"], question="total sales?"),
                dataset_name="sales.csv",
            )
        )
        assert result["answer"] == "Total sales are 1000 across 4 rows."
        assert result["confidence"] == "high"

        prompt = captured["messages"][-1]["content"]
        assert "Widget,East,400" in prompt  # real row from the CSV
        assert "sales" in prompt
        assert "sum=1000" in prompt  # aggregate computed from the data
        assert result["evidence"], "evidence should carry the computed aggregates"
        assert any("sum=1000" in line for line in result["evidence"])


class TestLegacyDatasetRouter:
    """``/api/v1/datasets`` used to return empty/fake payloads — it must now
    read and write the same registry as ``/ai/de/*``."""

    def test_create_upload_list_preview_roundtrip(self, client: TestClient):
        resp = client.post(
            "/api/v1/datasets/",
            json={"name": "legacy sales"},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 200, resp.text
        created = resp.json()
        assert created["id"]
        assert created["status"] == "draft"
        _uploaded.append(created["id"])

        resp = client.post(
            f"/api/v1/datasets/{created['id']}/upload",
            files={"file": ("legacy.csv", CSV_BYTES, "text/csv")},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 200, resp.text
        uploaded = resp.json()
        assert uploaded["row_count"] == CSV_ROWS
        assert uploaded["status"] == "ready"

        resp = client.get("/api/v1/datasets/", headers=_auth(ORG_A))
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()]
        assert created["id"] in ids

        resp = client.get(
            f"/api/v1/datasets/{created['id']}/preview", headers=_auth(ORG_A)
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["row_count"] == CSV_ROWS
        assert any(row.get("product") == "Widget" for row in body["rows"])

    def test_legacy_upload_rejects_other_org(self, client: TestClient):
        resp = client.post(
            "/api/v1/datasets/",
            json={"name": "org a only"},
            headers=_auth(ORG_A),
        )
        did = resp.json()["id"]
        _uploaded.append(did)

        resp = client.post(
            f"/api/v1/datasets/{did}/upload",
            files={"file": ("x.csv", CSV_BYTES, "text/csv")},
            headers=_auth(ORG_B),
        )
        assert resp.status_code == 404

        resp = client.get(f"/api/v1/datasets/{did}/preview", headers=_auth(ORG_B))
        assert resp.status_code == 404

    def test_legacy_upload_rejects_empty_file(self, client: TestClient):
        resp = client.post(
            "/api/v1/datasets/",
            json={"name": "empty target"},
            headers=_auth(ORG_A),
        )
        did = resp.json()["id"]
        _uploaded.append(did)

        resp = client.post(
            f"/api/v1/datasets/{did}/upload",
            files={"file": ("e.csv", b"", "text/csv")},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 400

    def test_legacy_upload_rejects_unreadable_file(self, client: TestClient):
        resp = client.post(
            "/api/v1/datasets/",
            json={"name": "broken target"},
            headers=_auth(ORG_A),
        )
        did = resp.json()["id"]
        _uploaded.append(did)

        resp = client.post(
            f"/api/v1/datasets/{did}/upload",
            files={"file": ("b.csv", b"\x00\x01\x02", "text/csv")},
            headers=_auth(ORG_A),
        )
        assert resp.status_code == 400

    def test_legacy_list_is_org_scoped(self, client: TestClient):
        resp = client.get("/api/v1/datasets/", headers=_auth(ORG_B))
        assert resp.status_code == 200
        assert resp.json() == []
