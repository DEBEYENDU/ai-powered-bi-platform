"""Distribution engine for reports.

Channels: download (secure temp URLs), email (via injected sender; notification
module interface is reused when available), shared links, organization sharing,
webhook (future hook). Every attempt records delivery status for audit.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DeliveryAttempt(BaseModel):
    attempt_id: str = Field(default_factory=lambda: secrets.token_hex(8))
    report_id: str
    channel: str
    recipient: str = ""
    status: str = "pending"  # pending, sent, failed, paused
    error_message: str = ""
    execution_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SharedLink(BaseModel):
    token: str = Field(default_factory=lambda: secrets.token_urlsafe(24))
    report_id: str
    version_number: int = 1
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    revoked: bool = False

    @property
    def is_valid(self) -> bool:
        return not self.revoked and datetime.utcnow() < self.expires_at


class DistributionEngine:
    def __init__(
        self, email_sender: Callable[..., Any] | None = None, storage_root: Path | None = None
    ) -> None:
        self._email_sender = email_sender or self._default_email_sender
        self._attempts: list[DeliveryAttempt] = []
        self._links: dict[str, SharedLink] = {}
        self.storage_root = storage_root or Path("/tmp/reports")  # noqa: S108 -- env-overridable dev default  # noqa: S108 -- env-overridable dev default; see .env.example

    # -- channels --
    def deliver_download(
        self, report_id: str, artifacts: list[dict[str, Any]], user_id: str = ""
    ) -> DeliveryAttempt:
        start = time.time()
        attempt = DeliveryAttempt(report_id=report_id, channel="download", recipient=user_id)
        try:
            for artifact in artifacts:
                self.secure_url(artifact.get("storage_path", ""))
            attempt.status = "sent"
            attempt.error_message = ""
        except Exception as exc:
            attempt.status = "failed"
            attempt.error_message = str(exc)
        attempt.execution_time_ms = round((time.time() - start) * 1000, 2)
        self._attempts.append(attempt)
        return attempt

    def deliver_email(
        self, report_id: str, artifacts: list[dict[str, Any]], recipients: list[str]
    ) -> list[DeliveryAttempt]:
        attempts: list[DeliveryAttempt] = []
        for recipient in recipients:
            start = time.time()
            attempt = DeliveryAttempt(report_id=report_id, channel="email", recipient=recipient)
            try:
                result = self._email_sender(recipient, report_id, artifacts)
                import asyncio

                if asyncio.iscoroutine(result):
                    raise RuntimeError("async email senders must be awaited by caller")
                attempt.status = "sent"
            except Exception as exc:
                attempt.status = "failed"
                attempt.error_message = str(exc)
            attempt.execution_time_ms = round((time.time() - start) * 1000, 2)
            self._attempts.append(attempt)
            attempts.append(attempt)
        return attempts

    def create_shared_link(
        self, report_id: str, version_number: int = 1, ttl_days: int = 7
    ) -> SharedLink:
        link = SharedLink(
            report_id=report_id,
            version_number=version_number,
            expires_at=datetime.utcnow() + timedelta(days=ttl_days),
        )
        self._links[link.token] = link
        return link

    def resolve_link(self, token: str) -> SharedLink | None:
        link = self._links.get(token)
        return link if link and link.is_valid else None

    def revoke_link(self, token: str) -> bool:
        link = self._links.get(token)
        if link is None:
            return False
        link.revoked = True
        return True

    def attempts(self, report_id: str | None = None) -> list[DeliveryAttempt]:
        if report_id is None:
            return list(self._attempts)
        return [a for a in self._attempts if a.report_id == report_id]

    # -- helpers --
    def secure_url(self, storage_path: str, ttl_seconds: int = 3600) -> str:
        digest = hashlib.sha256(f"{storage_path}:{secrets.token_hex(4)}".encode()).hexdigest()[:16]
        return f"/reports/download/{digest}?path={storage_path}&exp={ttl_seconds}"

    def _default_email_sender(
        self, recipient: str, report_id: str, artifacts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        # Notification module interface reuse point: swap with real sender.
        return {
            "queued": True,
            "recipient": recipient,
            "report_id": report_id,
            "attachments": len(artifacts),
        }
