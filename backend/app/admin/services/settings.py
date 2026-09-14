"""System settings with validation + maintenance windows.

Known setting keys are validated (rate limits positive, retention days sane,
log levels known). Maintenance mode: off / readonly / maintenance, with
scheduled windows and admin override tokens.
"""

from __future__ import annotations

import contextlib
import secrets
from datetime import datetime
from typing import Any

from app.admin.repositories import db_store
from app.core.logging import get_logger

log = get_logger(__name__)

VALIDATORS = {
    "rate_limit_per_minute": lambda v: isinstance(v, int) and v > 0,
    "log_level": lambda v: v in ("DEBUG", "INFO", "WARNING", "ERROR"),
    "retention_days_audit": lambda v: isinstance(v, int) and 1 <= v <= 3650,
    "retention_days_metrics": lambda v: isinstance(v, int) and 1 <= v <= 365,
    "maintenance_mode": lambda v: v in ("off", "readonly", "maintenance"),
}

DEFAULTS: dict[str, Any] = {
    "rate_limit_per_minute": 120,
    "log_level": "INFO",
    "retention_days_audit": 365,
    "retention_days_metrics": 90,
    "maintenance_mode": "off",
}


class SettingsService:
    def __init__(self) -> None:
        self._settings: dict[str, Any] = dict(DEFAULTS)
        self._updated_by: dict[str, str] = {}
        self._maintenance: dict[str, Any] = {
            "mode": "off",
            "message": "",
            "starts_at": None,
            "ends_at": None,
        }
        self._override_tokens: dict[str, str] = {}

    def get(self, key: str) -> Any:
        if key not in self._settings:
            raise ValueError(f"Unknown setting '{key}'")
        return self._settings[key]

    def all(self) -> dict[str, Any]:
        return dict(self._settings)

    def update(self, key: str, value: Any, updated_by: str = "") -> Any:
        validator = VALIDATORS.get(key)
        if validator is None:
            raise ValueError(f"Unknown setting '{key}'")
        if not validator(value):
            raise ValueError(f"Invalid value for '{key}': {value!r}")
        self._settings[key] = value
        self._updated_by[key] = updated_by
        with contextlib.suppress(Exception):
            db_store.setting_upsert(key, value, updated_by)
        return value

    # -- maintenance --
    def set_maintenance(
        self,
        mode: str,
        message: str = "",
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        created_by: str = "",
    ) -> dict[str, Any]:
        if mode not in ("off", "readonly", "maintenance"):
            raise ValueError(f"Unknown maintenance mode '{mode}'")
        previous = self._maintenance.get("mode")
        self._maintenance = {
            "mode": mode,
            "message": message,
            "starts_at": starts_at.isoformat() if starts_at else None,
            "ends_at": ends_at.isoformat() if ends_at else None,
            "created_by": created_by,
        }
        self._settings["maintenance_mode"] = mode
        log.info(
            "maintenance_mode_changed",
            previous=previous,
            current=mode,
            settings_id=id(self),
        )
        with contextlib.suppress(Exception):
            db_store.setting_upsert("maintenance_mode", mode, created_by)
            db_store.maintenance_save(
                {
                    "mode": mode,
                    "message": message,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "created_by": created_by,
                }
            )
        return self._maintenance

    def maintenance_status(self) -> dict[str, Any]:
        # Hydrate once from the persisted window so restarts resume the
        # last mode instead of silently resetting to "off".
        if not getattr(self, "_maintenance_loaded", False):
            self._maintenance_loaded = True
            with contextlib.suppress(Exception):
                latest = db_store.maintenance_latest()
                if latest and latest.get("mode") in ("off", "readonly", "maintenance"):
                    self._maintenance.update({k: v for k, v in latest.items() if v is not None})
                    self._settings["maintenance_mode"] = self._maintenance["mode"]
                    log.info(
                        "maintenance_hydrated_from_db",
                        mode=self._maintenance["mode"],
                        settings_id=id(self),
                    )
        result = dict(self._maintenance)
        result["is_write_blocked"] = self.is_write_blocked()
        return result

    def is_write_blocked(self) -> bool:
        return self._maintenance["mode"] in ("readonly", "maintenance")

    def mint_override_token(self, admin_id: str) -> str:
        token = secrets.token_urlsafe(24)
        self._override_tokens[token] = admin_id
        return token

    def check_override(self, token: str | None) -> bool:
        return bool(token) and token in self._override_tokens

    def overrides(self) -> list[str]:
        return list(self._override_tokens.values())
