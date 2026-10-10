"""Refresh-token transport tests.

The refresh token must travel in the request body. A token in the URL query
string leaks into access logs, proxies and browser history, so the query form
has to be rejected, not merely unused.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_refresh_token
from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def refresh_token() -> str:
    from app.admin.services.platform import get_platform

    users = get_platform().users._merged()
    assert users, "no users available to build a refresh token for"
    user_id = next(iter(users))
    return create_refresh_token({"sub": user_id})


class TestRefreshTransport:
    def test_refresh_accepts_token_in_body(self, client: TestClient, refresh_token: str):
        resp = client.post("/api/v1/auth/refresh", json={"token": refresh_token})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["access_token"]
        assert body["refresh_token"]

    def test_refresh_rejects_token_in_query_string(
        self, client: TestClient, refresh_token: str
    ):
        resp = client.post(f"/api/v1/auth/refresh?token={refresh_token}")
        assert resp.status_code == 422, resp.text
        assert "access_token" not in resp.text

    def test_refresh_rejects_empty_body(self, client: TestClient):
        resp = client.post("/api/v1/auth/refresh", json={})
        assert resp.status_code == 422

    def test_refresh_rejects_garbage_token_in_body(self, client: TestClient):
        resp = client.post("/api/v1/auth/refresh", json={"token": "not-a-jwt"})
        assert resp.status_code == 401
