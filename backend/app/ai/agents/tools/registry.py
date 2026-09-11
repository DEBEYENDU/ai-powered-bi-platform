"""Tool registry — shared tools that agents can access."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class ToolRegistry:
    """Registry of callable tools available to agents."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._call_log: list[dict[str, Any]] = []

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        description: str = "",
        agent_types: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self._tools[name] = {
            "func": func,
            "description": description,
            "agent_types": agent_types or [],
            "parameters": parameters or {},
            "enabled": True,
        }

    def call(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Call a tool and log the invocation."""
        if name not in self._tools:
            return {"error": f"Tool '{name}' not found"}
        tool = self._tools[name]
        if not tool["enabled"]:
            return {"error": f"Tool '{name}' is disabled"}

        t0 = time.perf_counter()
        try:
            result = tool["func"](**kwargs)
            duration = (time.perf_counter() - t0) * 1000
            self._call_log.append(
                {
                    "tool": name,
                    "status": "success",
                    "duration_ms": round(duration, 1),
                    "timestamp": time.time(),
                }
            )
            return {"success": True, "result": result, "duration_ms": round(duration, 1)}
        except Exception as exc:
            duration = (time.perf_counter() - t0) * 1000
            self._call_log.append(
                {
                    "tool": name,
                    "status": "error",
                    "error": str(exc),
                    "duration_ms": round(duration, 1),
                    "timestamp": time.time(),
                }
            )
            return {"success": False, "error": str(exc)}

    def get(self, name: str) -> Any:
        tool = self._tools.get(name)
        return tool["func"] if tool else None

    def list_tools(self, agent_type: str | None = None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for name, tool in self._tools.items():
            if agent_type and tool["agent_types"] and agent_type not in tool["agent_types"]:
                continue
            result.append(
                {
                    "name": name,
                    "description": tool["description"],
                    "agent_types": tool["agent_types"],
                    "enabled": tool["enabled"],
                }
            )
        return result

    def get_call_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._call_log[-limit:]


# --- Built-in tools ---


def _sql_execute(query: str, connection_string: str = "") -> dict[str, Any]:
    """Execute a SQL query (placeholder — wired to real DB in production)."""
    return {"columns": [], "rows": [], "row_count": 0, "query": query}


def _dashboard_build(config: dict[str, Any]) -> dict[str, Any]:
    """Build a dashboard from configuration."""
    return {"dashboard_id": f"dash_{int(time.time())}", "config": config, "status": "created"}


def _report_generate(config: dict[str, Any]) -> dict[str, Any]:
    """Generate a report from configuration."""
    return {"report_id": f"rpt_{int(time.time())}", "config": config, "status": "generated"}


def _email_send(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email notification."""
    return {"to": to, "subject": subject, "status": "sent"}


def _notification_send(user_id: str, message: str) -> dict[str, Any]:
    """Send an in-app notification."""
    return {"user_id": user_id, "message": message, "status": "delivered"}


def _file_upload(filename: str, content: bytes) -> dict[str, Any]:
    """Upload a file to storage."""
    return {"filename": filename, "size": len(content), "status": "uploaded"}


def _document_search(query: str, limit: int = 5) -> dict[str, Any]:
    """Search uploaded documents."""
    return {"query": query, "results": [], "count": 0}


def _storage_read(path: str) -> dict[str, Any]:
    """Read from storage."""
    return {"path": path, "content": "", "exists": False}


def _storage_write(path: str, content: str) -> dict[str, Any]:
    """Write to storage."""
    return {"path": path, "size": len(content), "status": "written"}


def register_default_tools(registry: ToolRegistry) -> None:
    """Register all default tools."""
    registry.register("sql_execute", _sql_execute, "Execute SQL queries", ["sql"])
    registry.register(
        "dashboard_build", _dashboard_build, "Build dashboards", ["dashboard", "visualization"]
    )
    registry.register("report_generate", _report_generate, "Generate reports", ["report"])
    registry.register("email_send", _email_send, "Send email notifications", ["workflow"])
    registry.register(
        "notification_send", _notification_send, "Send in-app notifications", ["workflow"]
    )
    registry.register(
        "file_upload", _file_upload, "Upload files to storage", ["report", "workflow"]
    )
    registry.register("document_search", _document_search, "Search documents", ["knowledge"])
    registry.register("storage_read", _storage_read, "Read from storage", ["sql", "knowledge"])
    registry.register("storage_write", _storage_write, "Write to storage", ["report", "dashboard"])


# Singleton
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        register_default_tools(_tool_registry)
    return _tool_registry
