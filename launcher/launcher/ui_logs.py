"""Live log viewer window: tabs, search, copy, save, auto-scroll."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from tkinter import filedialog
from typing import Any

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - GUI dependency
    ctk = None  # type: ignore

from launcher.logs import LogStore

CHANNELS = ["backend", "frontend", "redis", "launcher"]


class LogViewer:
    def __init__(self, parent, logs: LogStore) -> None:
        if ctk is None:
            raise RuntimeError("customtkinter is not installed")
        self.logs = logs
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Logs — BI Platform Launcher")
        self.window.geometry("900x600")
        self._pending: dict[str, list[str]] = {c: [] for c in CHANNELS}
        self._unsubs: list[Callable[[], None]] = []
        self._build()
        for channel in CHANNELS:
            self._unsubs.append(logs.subscribe(channel, self._make_appender(channel)))
        self.window.after(300, self._flush)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self) -> None:
        toolbar = ctk.CTkFrame(self.window)
        toolbar.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(toolbar, text="Search:").pack(side="left", padx=4)
        self.search_var = ctk.StringVar()
        search = ctk.CTkEntry(toolbar, textvariable=self.search_var, width=220)
        search.pack(side="left", padx=4)
        search.bind("<KeyRelease>", lambda _e: self._refresh_visible())
        self.auto_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(toolbar, text="Auto-scroll", variable=self.auto_var).pack(side="left", padx=8)
        ctk.CTkButton(toolbar, text="Copy", width=70, command=self._copy).pack(side="right", padx=4)
        ctk.CTkButton(toolbar, text="Save", width=70, command=self._save).pack(side="right", padx=4)
        ctk.CTkButton(toolbar, text="Clear", width=70, command=self._clear).pack(
            side="right", padx=4
        )
        self.tabs = ctk.CTkTabview(self.window)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.boxes: dict[str, Any] = {}
        for channel in CHANNELS:
            tab = self.tabs.add(channel.capitalize())
            box = ctk.CTkTextbox(tab, font=("Consolas", 12))
            box.pack(fill="both", expand=True)
            box.configure(state="disabled")
            self.boxes[channel] = box
        self._refresh_visible()

    def _current_channel(self) -> str:
        try:
            return self.tabs.get().lower()
        except Exception:
            return "backend"

    def _make_appender(self, channel: str) -> Callable[[str], None]:
        def append(line: str) -> None:
            self._pending[channel].append(line)

        return append

    def _flush(self) -> None:
        try:
            if not self.window.winfo_exists():
                return
            for channel, lines in self._pending.items():
                if not lines:
                    continue
                box = self.boxes[channel]
                box.configure(state="normal")
                box.insert("end", "\n".join(lines) + "\n")
                del lines[:]
                # Cap widget content to avoid unbounded growth.
                content_lines = int(box.index("end-1c").split(".")[0])
                if content_lines > 6000:
                    box.delete("1.0", f"{content_lines - 5000}.0")
                if self.auto_var.get() and channel == self._current_channel():
                    box.see("end")
                box.configure(state="disabled")
        finally:
            with contextlib.suppress(Exception):
                self.window.after(300, self._flush)

    def _refresh_visible(self) -> None:
        query = self.search_var.get().strip().lower()
        channel = self._current_channel()
        box = self.boxes[channel]
        lines = self.logs.lines(channel)
        if query:
            lines = [line for line in lines if query in line.lower()]
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("end", "\n".join(lines[-2000:]))
        if self.auto_var.get():
            box.see("end")
        box.configure(state="disabled")

    def _copy(self) -> None:
        box = self.boxes[self._current_channel()]
        text = box.get("1.0", "end-1c")
        self.window.clipboard_clear()
        self.window.clipboard_append(text)

    def _save(self) -> None:
        channel = self._current_channel()
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            initialfile=f"{channel}.log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(self.logs.lines(channel)))

    def _clear(self) -> None:
        channel = self._current_channel()
        self.logs.clear(channel)
        box = self.boxes[channel]
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.configure(state="disabled")

    def close(self) -> None:
        for unsub in self._unsubs:
            with contextlib.suppress(Exception):
                unsub()
        with contextlib.suppress(Exception):
            self.window.destroy()
