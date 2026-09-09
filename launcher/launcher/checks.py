"""Dependency detection: python, node, npm, postgres, redis, docker, env.

Every check returns a CheckResult (ok + human message) and never raises —
the UI shows friendly warnings instead of stack traces.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from launcher.paths import ProjectPaths


@dataclass
class CheckResult:
    ok: bool
    message: str
    detail: str = ""


def check_python() -> CheckResult:
    import sys

    return CheckResult(True, f"Python {sys.version.split()[0]}", sys.executable)


def _tool_version(binary: str, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            [binary, *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        first = (completed.stdout or completed.stderr or "").strip().splitlines()
        return first[0].strip() if first else "found"
    except (OSError, subprocess.SubprocessError) as exc:
        return f"error: {exc}"


def check_node() -> CheckResult:
    path = shutil.which("node")
    if not path:
        return CheckResult(False, "Node.js is not installed.", "Install Node.js 20+ LTS.")
    return CheckResult(True, f"Node.js {_tool_version('node', ['--version'])}", path)


def check_npm() -> CheckResult:
    for binary in ("npm.cmd", "npm"):
        if shutil.which(binary):
            return CheckResult(True, f"npm {_tool_version(binary, ['--version'])}", binary)
    return CheckResult(False, "npm is not installed.", "It ships with Node.js.")


def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_postgres(host: str = "localhost", port: int = 5432) -> CheckResult:
    if check_port_open(host, port):
        return CheckResult(True, f"PostgreSQL is running on {host}:{port}.")
    return CheckResult(
        False,
        "PostgreSQL is not running.",
        "Start your PostgreSQL service; the launcher and API will keep working without it.",
    )


def check_redis(host: str = "localhost", port: int = 6379) -> CheckResult:
    if check_port_open(host, port):
        return CheckResult(True, f"Redis is running on {host}:{port}.")
    return CheckResult(False, "Redis is not running.", "The app degrades gracefully without Redis.")


def check_docker() -> CheckResult:
    path = shutil.which("docker")
    if not path:
        return CheckResult(False, "Docker is not installed.", "")
    try:
        completed = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if completed.returncode == 0:
            return CheckResult(True, "Docker Desktop is running.", path)
        return CheckResult(False, "Docker is installed but not running.", "")
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(False, "Docker check failed.", str(exc))


def check_dotenv(paths: ProjectPaths) -> CheckResult:
    if paths.dotenv.is_file():
        return CheckResult(True, ".env found.", str(paths.dotenv))
    if paths.dotenv_example.is_file():
        try:
            paths.dotenv.write_text(
                paths.dotenv_example.read_text(encoding="utf-8"), encoding="utf-8"
            )
            return CheckResult(True, ".env created from .env.example.", str(paths.dotenv))
        except OSError as exc:
            return CheckResult(False, ".env is missing.", str(exc))
    return CheckResult(False, ".env and .env.example are both missing.", "")


def ensure_dir(path: Path) -> CheckResult:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return CheckResult(True, f"Folder ready: {path}")
    except OSError as exc:
        return CheckResult(False, f"Cannot create folder: {path}", str(exc))


def docker_container_running(name: str) -> bool:
    try:
        completed = subprocess.run(
            ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return name in (completed.stdout or "").split()
    except (OSError, subprocess.SubprocessError):
        return False


def ensure_redis_container(name: str = "bi-redis", port: int = 6379) -> CheckResult:
    """Start (or create) a Redis container. Never raises; warns instead."""
    if not shutil.which("docker"):
        return CheckResult(False, "Docker is not installed.", "Start Redis manually.")
    if docker_container_running(name):
        return CheckResult(True, f"Redis container '{name}' is already running.")
    try:
        existing = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if name in (existing.stdout or "").split():
            started = subprocess.run(
                ["docker", "start", name],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if started.returncode == 0:
                return CheckResult(True, f"Redis container '{name}' started.")
        created = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-p",
                f"{port}:6379",
                "redis:7-alpine",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if created.returncode == 0:
            return CheckResult(True, f"Redis container '{name}' created and started.")
        return CheckResult(False, "Could not start Redis container.", created.stderr.strip()[:300])
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(False, "Could not start Redis container.", str(exc)[:300])


def git_info(root: Path) -> dict[str, str]:
    info = {"branch": "?", "commit": "?", "version": "?"}
    with contextlib.suppress(Exception):
        info["branch"] = (
            subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            ).stdout.strip()
            or "?"
        )
        info["commit"] = (
            subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            ).stdout.strip()
            or "?"
        )
    with contextlib.suppress(Exception):
        from launcher import __version__

        info["version"] = __version__
    return info


def node_modules_present(paths: ProjectPaths) -> bool:
    return (paths.frontend_node_modules / ".package-lock.json").is_file() or (
        paths.frontend_node_modules.is_dir() and any(paths.frontend_node_modules.iterdir())
    )


def get_env_value(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
