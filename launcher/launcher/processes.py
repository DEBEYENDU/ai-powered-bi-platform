"""ProcessManager: start/stop/supervise backend, frontend, redis processes.

- Backend runs with ``backend/.venv/Scripts/python.exe`` when present,
  otherwise the current interpreter (with a logged warning).
- Frontend runs ``npm run dev`` via ``npm.cmd`` on Windows.
- Output streams are pumped to the LogStore AND log files.
- ``kill_orphans`` removes stray uvicorn/vite processes by command line.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from launcher.checks import node_modules_present
from launcher.logs import LogStore
from launcher.paths import ProjectPaths

WINDOWS = os.name == "nt"


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen | None = None
    started_at: float = 0.0
    stop_requested: bool = False

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @property
    def uptime_seconds(self) -> float:
        if not self.started_at:
            return 0.0
        return max(0.0, time.time() - self.started_at)


def _npm_binary() -> str:
    if WINDOWS:
        for candidate in ("npm.cmd", "npm"):
            try:
                subprocess.run(
                    [candidate, "--version"], capture_output=True, timeout=15, check=False
                )
                return candidate
            except (OSError, subprocess.SubprocessError):
                continue
        return "npm.cmd"
    return "npm"


class ProcessManager:
    def __init__(self, paths: ProjectPaths, logs: LogStore) -> None:
        self.paths = paths
        self.logs = logs
        self.backend = ManagedProcess("backend")
        self.frontend = ManagedProcess("frontend")
        self._lock = threading.Lock()
        self.on_change: Callable[[], None] | None = None

    # -- helpers --
    def _notify(self) -> None:
        if self.on_change:
            with contextlib.suppress(Exception):
                self.on_change()

    def _pump(self, managed: ManagedProcess, stream, channel: str) -> None:
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break
                self.logs.append(channel, line)
        except OSError as exc:
            self.logs.append(channel, f"[log pump ended: {exc}]")
        finally:
            with contextlib.suppress(Exception):
                stream.close()

    def _spawn(
        self,
        managed: ManagedProcess,
        command: list[str],
        cwd: Path,
        env_extra: dict[str, str] | None = None,
        channel: str = "",
    ) -> None:
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        channel = channel or managed.name
        creationflags = 0
        if WINDOWS:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        managed.process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
        managed.started_at = time.time()
        managed.stop_requested = False
        threading.Thread(
            target=self._pump, args=(managed, managed.process.stdout, channel), daemon=True
        ).start()
        self.logs.append(channel, f"$ {' '.join(command)}  (cwd={cwd})")
        self._notify()

    # -- backend --
    def backend_python(self) -> tuple[str, bool]:
        """Interpreter to use + whether it is the project venv."""
        if self.paths.has_venv():
            return str(self.paths.venv_python), True
        return sys.executable, False

    def start_backend(self, port: int, env_extra: dict[str, str] | None = None) -> None:
        with self._lock:
            if self.backend.running:
                self.logs.append("backend", "Backend is already running.")
                return
            python, is_venv = self.backend_python()
            if not is_venv:
                self.logs.append(
                    "backend",
                    "WARNING: backend/.venv not found, using current interpreter.",
                )
            self._spawn(
                self.backend,
                [
                    python,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--reload",
                ],
                cwd=self.paths.backend,
                env_extra={"PYTHONPATH": str(self.paths.backend), **(env_extra or {})},
                channel="backend",
            )

    def stop_backend(self) -> None:
        self._stop(self.backend)

    # -- frontend --
    def ensure_frontend_deps(self) -> bool:
        """Run npm install only when node_modules is missing. Returns success."""
        if node_modules_present(self.paths):
            self.logs.append("frontend", "node_modules present, skipping npm install.")
            return True
        self.logs.append("frontend", "Installing frontend packages (npm install)...")
        try:
            completed = subprocess.run(
                [_npm_binary(), "install"],
                cwd=str(self.paths.frontend),
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            self.logs.append("frontend", completed.stdout[-2000:] + completed.stderr[-2000:])
            return completed.returncode == 0
        except (OSError, subprocess.SubprocessError) as exc:
            self.logs.append("frontend", f"npm install failed: {exc}")
            return False

    def start_frontend(self, port: int) -> None:
        with self._lock:
            if self.frontend.running:
                self.logs.append("frontend", "Frontend is already running.")
                return
            self._spawn(
                self.frontend,
                [_npm_binary(), "run", "dev", "--", "--port", str(port), "--strictPort"],
                cwd=self.paths.frontend,
                channel="frontend",
            )

    def stop_frontend(self) -> None:
        self._stop(self.frontend)

    # -- generic --
    def _stop(self, managed: ManagedProcess, timeout: float = 10.0) -> None:
        with self._lock:
            proc = managed.process
            if proc is None or proc.poll() is not None:
                managed.process = None
                return
            managed.stop_requested = True
        self.logs.append(managed.name, "Stopping...")
        try:
            proc.terminate()
            proc.wait(timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            with contextlib.suppress(OSError):
                proc.kill()
        with self._lock:
            managed.process = None
        self.logs.append(managed.name, "Stopped.")
        self._notify()

    def stop_all(self) -> None:
        self.stop_backend()
        self.stop_frontend()

    def kill_orphans(self) -> int:
        """Kill stray uvicorn/vite processes not owned by this launcher."""
        killed = 0
        try:
            import psutil
        except ImportError:
            return 0
        owned = set()
        for managed in (self.backend, self.frontend):
            if managed.process is not None:
                with contextlib.suppress(Exception):
                    owned.add(managed.process.pid)
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                if proc.pid in owned:
                    continue
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                if ("uvicorn" in cmdline and "app.main" in cmdline) or (
                    "vite" in cmdline and "node_modules" in cmdline
                ):
                    proc.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        if killed:
            self.logs.append("launcher", f"Killed {killed} orphan process(es).")
        return killed

    def wait_ready(self, url: str, timeout: float = 90.0, label: str = "") -> bool:
        """Poll an HTTP URL until 2xx/3xx or timeout. Never raises."""
        import urllib.request

        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                procs = [self.backend.process, self.frontend.process]
            alive = any(p is not None and p.poll() is None for p in procs)
            if not alive and label:
                return False
            with contextlib.suppress(Exception), urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 400:
                    return True
            time.sleep(1.0)
        return False
