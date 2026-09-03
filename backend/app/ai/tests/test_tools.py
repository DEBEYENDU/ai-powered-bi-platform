"""Tests for AI Tools."""

import pytest
from app.ai.tools.registry import ToolRegistry, ToolDefinition


class TestToolRegistry:
    def test_registry_initialization(self):
        registry = ToolRegistry()
        tools = registry.list_tools()
        assert len(tools) > 0
        assert "calculate_kpi" in tools

    def test_tool_registration(self):
        registry = ToolRegistry()
        assert registry.has("calculate_kpi")
        assert registry.has("revenue_analytics")

    def test_tool_definition(self):
        registry = ToolRegistry()
        tool = registry.get("calculate_kpi")
        assert tool is not None
        assert tool.permission_required == "analytics:read"

    def test_tool_caching(self):
        registry = ToolRegistry()
        tool = registry.get("calculate_kpi")
        assert tool.cacheable is True