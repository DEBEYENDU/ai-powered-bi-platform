"""Project-root resolution without hardcoded paths.

Works in three layouts:
1. Source checkout: <root>/launcher/launcher/paths.py  -> root = parents[2].
2. Frozen exe next to the project (portable): exe dir whose parent (or self)
   contains backend/ + frontend/ markers.
3. Fallback: walk upward from CWD looking for the markers.
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKERS = ("backend", "frontend")


def _has_markers(directory: Path) -> bool:
    return all((directory / marker).is_dir() for marker in MARKERS)


def find_project_root() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (exe_dir, exe_dir.parent):
            if _has_markers(candidate):
                return candidate
    else:
        source_root = Path(__file__).resolve().parents[2]
        if _has_markers(source_root):
            return source_root
    current: Path | None = Path.cwd().resolve()
    while current is not None:
        if _has_markers(current):
            return current
        current = current.parent if current.parent != current else None
    return Path.cwd()


class ProjectPaths:
    """All launcher paths derived from a single root."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or find_project_root()).resolve()
        self.backend = self.root / "backend"
        self.frontend = self.root / "frontend"
        self.launcher_dir = self.root / "launcher"
        self.logs_dir = self.launcher_dir / "logs"
        self.venv_python = self.backend / ".venv" / "Scripts" / "python.exe"
        self.dotenv = self.backend / ".env"
        self.dotenv_example = self.backend / ".env.example"
        self.frontend_node_modules = self.frontend / "node_modules"
        self.frontend_package = self.frontend / "package.json"
        self.config_file = self.launcher_dir / "launcher_config.json"

    def has_backend(self) -> bool:
        return (self.backend / "app" / "main.py").is_file()

    def has_frontend(self) -> bool:
        return self.frontend_package.is_file()

    def has_venv(self) -> bool:
        return self.venv_python.is_file()
