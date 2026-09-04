"""Model Context Protocol (MCP) layer for AI Business Assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    name: str
    description: str
    server: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    sandboxed: bool = True


class MCPServerInfo(BaseModel):
    server_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    capabilities: list[str] = Field(default_factory=list)
    authenticated: bool = False
    registered_at: datetime = Field(default_factory=datetime.utcnow)


class MCPRegistry:
    """Registry for MCP servers and tools with discovery and audit."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerInfo] = {}
        self._tools: dict[str, MCPTool] = {}
        self._audit_log: list[dict[str, Any]] = []
        self._register_builtin_servers()

    def _register_builtin_servers(self) -> None:
        builtin = [
            ("analytics_mcp", ["revenue_analytics", "sales_analytics", "calculate_kpi"]),
            ("database_mcp", ["query", "schema_inspect"]),
            ("dashboard_mcp", ["get_dashboard", "get_dashboard_summary"]),
            ("filesystem_mcp", ["read", "list"]),
            ("report_mcp", ["generate_report", "generate_executive_summary"]),
            ("forecast_mcp", ["run_forecast", "predict"]),
            ("notification_mcp", ["send_notification"]),
            ("external_api_mcp", ["http_get", "http_post"]),
        ]
        for name, caps in builtin:
            info = MCPServerInfo(name=name, capabilities=caps, authenticated=True)
            self._servers[name] = info
            for cap in caps:
                self._tools[cap] = MCPTool(name=cap, description=f"{cap} via {name}", server=name)

    def discover_servers(self) -> list[MCPServerInfo]:
        return list(self._servers.values())

    def negotiate_capabilities(self, server_name: str) -> list[str]:
        server = self._servers.get(server_name)
        return server.capabilities if server else []

    def check_permission(self, tool_name: str, user_permissions: list[str]) -> bool:
        tool = self._tools.get(tool_name)
        if tool is None:
            return False
        if not tool.permissions:
            return True
        return any(p in user_permissions for p in tool.permissions)

    def audit(self, action: str, details: dict[str, Any]) -> None:
        self._audit_log.append(
            {
                "action": action,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def list_tools(self) -> list[MCPTool]:
        return list(self._tools.values())

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._audit_log[-limit:]
