"""Settings dialog: validated editing of launcher_config.json."""

from __future__ import annotations

import contextlib
from collections.abc import Callable

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - GUI dependency
    ctk = None  # type: ignore

from launcher.config import SettingsManager

FIELDS: list[tuple[str, str]] = [
    ("backend_port", "Backend port"),
    ("frontend_port", "Frontend port"),
    ("database_url", "Database URL"),
    ("redis_url", "Redis URL"),
    ("storage_path", "Storage path (empty = project default)"),
    ("reports_path", "Reports path (empty = project default)"),
    ("redis_container", "Redis container name"),
]


class SettingsDialog:
    def __init__(
        self,
        parent,
        settings: SettingsManager,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        if ctk is None:
            raise RuntimeError("customtkinter is not installed")
        self.settings = settings
        self.on_saved = on_saved
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Settings")
        self.window.geometry("560x620")
        self.vars: dict[str, object] = {}
        self._build()

    def _build(self) -> None:
        frame = ctk.CTkScrollableFrame(self.window)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        for key, label in FIELDS:
            ctk.CTkLabel(frame, text=label).pack(anchor="w", pady=(8, 0))
            var = ctk.StringVar(value=str(self.settings.get(key)))
            ctk.CTkEntry(frame, textvariable=var).pack(fill="x")
            self.vars[key] = var
        ctk.CTkLabel(frame, text="Theme").pack(anchor="w", pady=(8, 0))
        self.theme_var = ctk.StringVar(value=str(self.settings.get("theme")))
        ctk.CTkOptionMenu(frame, values=["dark", "light"], variable=self.theme_var).pack(anchor="w")
        self.browser_var = ctk.BooleanVar(value=bool(self.settings.get("auto_start_browser")))
        ctk.CTkSwitch(frame, text="Auto-open browser on start", variable=self.browser_var).pack(
            anchor="w", pady=8
        )
        self.redis_var = ctk.BooleanVar(value=bool(self.settings.get("manage_redis_container")))
        ctk.CTkSwitch(frame, text="Auto-manage Redis container", variable=self.redis_var).pack(
            anchor="w", pady=4
        )
        self.error_label = ctk.CTkLabel(frame, text="", text_color="red")
        self.error_label.pack(anchor="w", pady=4)
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x", pady=8)
        ctk.CTkButton(buttons, text="Save", command=self._save).pack(side="right", padx=4)
        ctk.CTkButton(buttons, text="Cancel", fg_color="gray", command=self.window.destroy).pack(
            side="right", padx=4
        )

    def _save(self) -> None:
        try:
            for key, _ in FIELDS:
                var = self.vars[key]
                if not isinstance(var, ctk.StringVar):
                    continue
                value: object = var.get()
                if key in ("backend_port", "frontend_port"):
                    value = int(str(value).strip())
                self.settings.set(key, value)
            self.settings.set("theme", self.theme_var.get())
            self.settings.set("auto_start_browser", bool(self.browser_var.get()))
            self.settings.set("manage_redis_container", bool(self.redis_var.get()))
            self.settings.save()
        except Exception as exc:
            self.error_label.configure(text=f"Invalid value: {exc}")
            return
        if self.on_saved:
            with contextlib.suppress(Exception):
                self.on_saved()
        self.window.destroy()
