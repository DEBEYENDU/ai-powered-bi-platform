"""SettingsManager: launcher_config.json with validated defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "backend_port": 8000,
    "frontend_port": 5173,
    "database_url": "postgresql+psycopg://bi:bi@localhost:5432/bi_platform",
    "redis_url": "redis://localhost:6379/0",
    "storage_path": "",
    "reports_path": "",
    "theme": "dark",
    "auto_start_browser": True,
    "redis_container": "bi-redis",
    "manage_redis_container": True,
}


class SettingsManager:
    def __init__(self, config_file: Path) -> None:
        self.config_file = config_file
        self._settings: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            stored = json.loads(self.config_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(stored, dict):
            for key, default in DEFAULTS.items():
                if key in stored and isinstance(stored[key], type(default)):
                    self._settings[key] = stored[key]

    def save(self) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")

    def get(self, key: str) -> Any:
        return self._settings.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        if key not in DEFAULTS:
            raise ValueError(f"Unknown setting: {key}")
        self._settings[key] = self.validate(key, value)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._settings)

    @staticmethod
    def validate(key: str, value: Any) -> Any:
        if key in ("backend_port", "frontend_port"):
            port = int(value)
            if not 1 <= port <= 65535:
                raise ValueError("Port must be 1-65535")
            return port
        if key in ("database_url", "redis_url"):
            text = str(value).strip()
            if "://" not in text:
                raise ValueError("URL must contain '://'")
            return text
        if key in ("storage_path", "reports_path"):
            return str(value).strip()
        if key == "theme":
            if str(value) not in ("dark", "light"):
                raise ValueError("Theme must be 'dark' or 'light'")
            return str(value)
        if key in ("auto_start_browser", "manage_redis_container"):
            return bool(value)
        if key == "redis_container":
            name = str(value).strip()
            if not name:
                raise ValueError("Container name must not be empty")
            return name
        return value
