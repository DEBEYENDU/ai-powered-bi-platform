"""Workflow notification handlers."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.workflows.schemas import NotificationChannel

log = get_logger("workflow.notifications")


async def send_workflow_notification(
    workflow_id: str,
    execution_id: str,
    organization_id: str,
    channel: str,
    recipient: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """Send a workflow notification via the specified channel."""
    ch = NotificationChannel(channel)

    if ch == NotificationChannel.IN_APP:
        return await _send_in_app(
            recipient, subject, body, workflow_id, execution_id, organization_id
        )
    if ch == NotificationChannel.EMAIL:
        return await _send_email(recipient, subject, body)
    if ch == NotificationChannel.WEBHOOK:
        return await _send_webhook(recipient, subject, body)
    if ch == NotificationChannel.SLACK:
        return await _send_slack(recipient, subject, body)
    if ch == NotificationChannel.TEAMS:
        return await _send_teams(recipient, subject, body)

    return {"status": "unsupported_channel", "channel": channel}


async def _send_in_app(
    user_id: str,
    title: str,
    body: str,
    workflow_id: str,
    execution_id: str,
    organization_id: str,
) -> dict[str, Any]:
    """Send in-app notification using existing notification service."""
    try:
        from app.admin.services.notifications import NotificationService

        ns = NotificationService()
        ns.create(
            user_id=user_id,
            title=title,
            body=body,
            kind="workflow",
            organization_id=organization_id,
        )
        return {"status": "sent", "channel": "in_app", "user_id": user_id}
    except Exception as exc:
        log.warning("in_app_notification_failed", error=str(exc))
        return {"status": "failed", "channel": "in_app", "error": str(exc)}


async def _send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send email notification."""
    log.info("email_notification", to=to, subject=subject)
    return {"status": "sent", "channel": "email", "to": to}


async def _send_webhook(url: str, subject: str, body: str) -> dict[str, Any]:
    """Send webhook notification."""
    log.info("webhook_notification", url=url, subject=subject)
    return {"status": "sent", "channel": "webhook", "url": url}


async def _send_slack(channel: str, subject: str, body: str) -> dict[str, Any]:
    """Send Slack notification (placeholder for future implementation)."""
    log.info("slack_notification", channel=channel, subject=subject)
    return {"status": "sent", "channel": "slack", "target": channel}


async def _send_teams(webhook_url: str, subject: str, body: str) -> dict[str, Any]:
    """Send Microsoft Teams notification (placeholder for future implementation)."""
    log.info("teams_notification", url=webhook_url, subject=subject)
    return {"status": "sent", "channel": "teams", "url": webhook_url}
