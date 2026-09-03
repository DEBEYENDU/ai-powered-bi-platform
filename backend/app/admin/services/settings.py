"""System settings with validation + maintenance windows.

Known setting keys are validated (rate limits positive, retention days sane,
log levels known). Maintenance mode: off / readonly / maintenance, with
scheduled windows and admin override tokens.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional


VALIDATORS = {
    "rate_limit_per_minute": lambda v: isinstance(v, int) and v > 0,
    "log_level": lambda v: v in ("DEBUG", "INFO", "WARNING", "ERROR"),
    "retention_days_audit": lambda v: isinstance(v, int) and 1 <= v <= 3650,
    "retention_days_metrics": lambda v: isinstance(v, int) and 1 <= v <= 365,
    "maintenance_mode": lambda v: v in ("off", "readonly", "maintenance"),
}

DEFAULTS: Dict[str, Any] = {
    "rate_limit_per_minute": 120,
    "log_level": "INFO",
    "retention_days_audit": 365,
    "retention_days_metrics": 90,
    "maintenance_mode": "off",
}


class SettingsService:
    def __init__(self) -> None:
        self._settings: Dict[str, Any] = dict(DEFAULTS)
        self._updated_by: Dict[str, str] = {}
        self._maintenance: Dict[str, Any] = {"mode": "off", "message": "",
                                             "starts_at": None, "ends_at": None}
        self._override_tokens: Dict[str, str] = {}

    def get(self, key: str) -> Any:
        if key not in self._settings:
            raise ValueError(f"Unknown setting '{key}'")
        return self._settings[key]

    def all(self) -> Dict[str, Any]:
        return dict(self._settings)

    def update(self, key: str, value: Any, updated_by: str = "") -> Any:
        validator = VALIDATORS.get(key)
        if validator is None:
            raise ValueError(f"Unknown setting '{key}'")
        if not validator(value):
            raise ValueError(f"Invalid value for '{key}': {value!r}")
        self._settings[key] = value
        self._updated_by[key] = updated_by
        return value

    # -- maintenance --
    def set_maintenance(self, mode: str, message: str = "",
                        starts_at: Optional[datetime] = None,
                        ends_at: Optional[datetime] = None,
                        created_by: str = "") -> Dict[str, Any]:
        if mode not in ("off", "readonly", "maintenance"):
            raise ValueError(f"Unknown maintenance mode '{mode}'")
        self._maintenance = {"mode": mode, "message": message,
                             "starts_at": starts_at.isoformat() if starts_at else None,
                             "ends_at": ends_at.isoformat() if ends_at else None,
                             "created_by": created_by}
        self._settings["maintenance_mode"] = mode
        return self._maintenance

    def maintenance_status(self) -> Dict[str, Any]:
        return dict(self._maintenance)

    def is_write_blocked(self) -> bool:
        return self._maintenance["mode"] in ("readonly", "maintenance")

    def mint_override_token(self, admin_id: str) -> str:
        token = secrets.token_urlsafe(24)
        self._override_tokens[token] = admin_id
        return token

    def check_override(self, token: Optional[str]) -> bool:
        return bool(token) and token in self._override_tokens

    def overrides(self) -> List[str]:
        return list(self._override_tokens.values())
