"""LogStore: thread-safe ring buffers + file sinks for every service.

Each managed process gets a named channel (backend, frontend, redis,
launcher). Writers append lines (also mirrored to a rotating-ish log file);
the log viewer subscribes for live updates.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path
from typing import Any


class LogStore:
    def __init__(self, logs_dir: Path, max_lines: int = 5000) -> None:
        self.logs_dir = logs_dir
        self.max_lines = max_lines
        self._lock = threading.Lock()
        self._buffers: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=max_lines))
        self._subscribers: dict[str, list[Callable[[str], None]]] = defaultdict(list)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _log_file(self, channel: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in channel)
        return self.logs_dir / f"{safe}.log"

    def append(self, channel: str, line: str) -> None:
        timestamped = f"[{time.strftime('%H:%M:%S')}] {line.rstrip()}"
        with self._lock:
            self._buffers[channel].append(timestamped)
            try:
                with self._log_file(channel).open("a", encoding="utf-8") as handle:
                    handle.write(timestamped + "\n")
            except OSError:
                pass
            subscribers = list(self._subscribers[channel])
        for callback in subscribers:
            with contextlib.suppress(Exception):
                callback(timestamped)

    def lines(self, channel: str, limit: int | None = None) -> list[str]:
        with self._lock:
            buffer = list(self._buffers[channel])
        return buffer[-limit:] if limit else buffer

    def search(self, channel: str, query: str) -> list[str]:
        query = query.lower()
        return [line for line in self.lines(channel) if query in line.lower()]

    def clear(self, channel: str) -> None:
        with self._lock:
            self._buffers[channel].clear()

    def channels(self) -> list[str]:
        with self._lock:
            return sorted(self._buffers.keys())

    def subscribe(self, channel: str, callback: Callable[[str], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers[channel].append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers[channel]:
                    self._subscribers[channel].remove(callback)

        return unsubscribe

    def info(self, message: str, channel: str = "launcher") -> None:
        self.append(channel, message)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {channel: len(buffer) for channel, buffer in self._buffers.items()}
