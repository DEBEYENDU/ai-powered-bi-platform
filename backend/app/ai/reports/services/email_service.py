"""Email delivery service for reports."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


class EmailService:
    """Send reports via email. Supports SMTP, with extension points for
    Microsoft 365, Gmail, SendGrid, Mailgun, Amazon SES."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    async def send_report(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        attachment_path: str | None = None,
        attachment_name: str | None = None,
    ) -> dict[str, Any]:
        """Send a report email via SMTP."""
        smtp_host = self._config.get("smtp_host", "")
        smtp_port = self._config.get("smtp_port", 587)
        smtp_user = self._config.get("smtp_user", "")
        smtp_pass = self._config.get("smtp_password", "")
        from_addr = self._config.get("from_email", smtp_user)

        if not smtp_host:
            return {
                "success": False,
                "error": "SMTP not configured. Set SMTP_HOST environment variable.",
                "channel": "email",
            }

        try:
            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            if attachment_path:
                import os
                if os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as f:
                        from email import encoders
                        from email.mime.base import MIMEBase
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        fname = attachment_name or os.path.basename(attachment_path)
                        part.add_header("Content-Disposition", f"attachment; filename={fname}")
                        msg.attach(part)

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, recipients, msg.as_string())

            return {
                "success": True,
                "channel": "email",
                "recipients": recipients,
                "subject": subject,
            }
        except Exception as e:  # noqa: BLE001
            return {
                "success": False,
                "error": str(e),
                "channel": "email",
                "recipients": recipients,
            }
