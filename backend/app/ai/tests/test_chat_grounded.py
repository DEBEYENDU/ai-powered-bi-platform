"""General AI chat must be grounded in the organization's dataset records.

Covers the reported failure mode where the assistant invented analysis of
business data it never saw ("Have I uploaded a dataset?" answered from the
model's training knowledge instead of the actual dataset records).
"""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.ai.providers.base import ChatChunk, ChatMessage, LLMResponse
from app.core.security import create_access_token
from app.main import app

CSV_BYTES = (
    b"product,region,sales\n"
    b"Widget,East,400\n"
    b"Widget,West,300\n"
    b"Gadget,East,200\n"
    b"Gizmo,North,100\n"
)

ORG_WITH_DATA = str(uuid.uuid4())
ORG_EMPTY = str(uuid.uuid4())
USER = str(uuid.uuid4())

_uploaded: list[str] = []
_conversations: list[str] = []


def _auth(org: str) -> dict[str, str]:
    token = create_access_token({"sub": USER, "organization_id": org})
    return {"Authorization": f"Bearer {token}"}


class FakeProvider:
    """Records the exact message history the service sends to the LLM."""

    name = "fake"

    def __init__(self) -> None:
        self.calls: list[list[ChatMessage]] = []

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: object,
    ) -> LLMResponse:
        self.calls.append(list(messages))
        return LLMResponse(
            content="grounded answer",
            model=model,
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            finish_reason="stop",
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: object,
    ):
        self.calls.append(list(messages))
        for piece in ("grounded ", "answer"):
            yield ChatChunk(delta=piece, finish_reason=None)
        yield ChatChunk(delta="", finish_reason="stop")


@pytest.fixture()
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    fake = FakeProvider()
    monkeypatch.setattr(
        "app.ai.services.chat_service.get_provider", lambda name=None: fake
    )
    return fake


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def uploaded(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/ai/de/upload",
        files={"file": ("sales.csv", CSV_BYTES, "text/csv")},
        headers=_auth(ORG_WITH_DATA),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True, body
    _uploaded.append(body["dataset_id"])
    return body


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    from pathlib import Path

    from app.ai.data_engineering.models import DatasetRecord
    from app.ai.models.conversation import Conversation
    from app.core.config import get_settings
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        for cid in _conversations:
            conv = db.get(Conversation, cid)
            if conv is not None:
                db.delete(conv)
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


def _system_of(fake: FakeProvider) -> str:
    assert fake.calls, "provider was never called"
    first = fake.calls[-1][0]
    assert first.role == "system"
    return first.content


class TestGroundedGeneralChat:
    def test_chat_knows_about_uploaded_datasets(
        self, client: TestClient, fake_provider: FakeProvider, uploaded: dict
    ):
        resp = client.post(
            "/api/v1/ai/chat",
            json={"message": "Have I uploaded a dataset?", "stream": False},
            headers=_auth(ORG_WITH_DATA),
        )
        assert resp.status_code == 200, resp.text
        system = _system_of(fake_provider)
        assert "sales.csv" in system
        assert "(4 rows, 3 columns)" in system
        assert "product, region, sales" in system
        assert "Never invent" in system

    def test_user_message_reaches_the_model_exactly_once(
        self, client: TestClient, fake_provider: FakeProvider
    ):
        question = "Have I uploaded a dataset?"
        resp = client.post(
            "/api/v1/ai/chat",
            json={"message": question, "stream": False},
            headers=_auth(ORG_WITH_DATA),
        )
        assert resp.status_code == 200
        msgs = fake_provider.calls[-1]
        user_msgs = [m for m in msgs if m.role == "user" and m.content == question]
        assert len(user_msgs) == 1, "user message must not be duplicated in history"

    def test_exactly_one_assistant_message_is_persisted(
        self, client: TestClient, fake_provider: FakeProvider
    ):
        resp = client.post(
            "/api/v1/ai/chat",
            json={"message": "What data do you have?", "stream": False},
            headers=_auth(ORG_WITH_DATA),
        )
        assert resp.status_code == 200
        conv_id = resp.json()["conversation_id"]
        _conversations.append(conv_id)
        detail = client.get(f"/api/v1/ai/conversations/{conv_id}", headers=_auth(ORG_WITH_DATA))
        assert detail.status_code == 200
        roles = [m["role"] for m in detail.json()["messages"]]
        assert roles == ["user", "assistant"]

    def test_streaming_chat_is_grounded_and_persisted_once(
        self, client: TestClient, fake_provider: FakeProvider, uploaded: dict
    ):
        resp = client.post(
            "/api/v1/ai/chat",
            json={"message": "Stream me a grounded answer", "stream": True},
            headers=_auth(ORG_WITH_DATA),
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert body.count("data: [DONE]") == 1
        deltas = [
            json.loads(line[6:])["delta"]
            for line in body.splitlines()
            if line.startswith("data: ")
            and line[6:].strip() not in ("[DONE]",)
            and "delta" in line
        ]
        assert "".join(d for d in deltas if d) == "grounded answer"
        # Grounded: the streamed request must also carry the dataset inventory.
        system = _system_of(fake_provider)
        assert "sales.csv" in system
        conv_id = ""
        for line in body.splitlines():
            if not line.startswith("data: ") or line[6:].strip() == "[DONE]":
                continue
            try:
                conv_id = json.loads(line[6:]).get("conversation_id") or conv_id
            except json.JSONDecodeError:
                continue
        assert conv_id, "streamed events must carry the conversation id"
        detail = client.get(f"/api/v1/ai/conversations/{conv_id}", headers=_auth(ORG_WITH_DATA))
        roles = [m["role"] for m in detail.json()["messages"]]
        assert roles == ["user", "assistant"], roles

    def test_chat_without_datasets_says_so_instead_of_inventing(
        self, client: TestClient, fake_provider: FakeProvider
    ):
        resp = client.post(
            "/api/v1/ai/chat",
            json={"message": "Analyze my revenue", "stream": False},
            headers=_auth(ORG_EMPTY),
        )
        assert resp.status_code == 200
        conv_id = resp.json()["conversation_id"]
        _conversations.append(conv_id)
        system = _system_of(fake_provider)
        assert "has not uploaded any datasets" in system
        assert "sales.csv" not in system
