"""Coordinator Agent for AI Business Assistant."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CoordinatorAgentConfig(BaseModel):
    name: str = "coordinator_agent"
    description: str = "Coordinates specialized AI agents"
    model: str = "gpt-4"
    temperature: float = 0.2


class CoordinatorAgent:
    """Coordinates specialized AI agents for query resolution."""

    def __init__(self, config: CoordinatorAgentConfig | None = None) -> None:
        self.config = config or CoordinatorAgentConfig()
        self.name = self.config.name
        self.agents: dict[str, Any] = {}

    def register_agent(self, name: str, agent: Any) -> None:
        self.agents[name] = agent

    def get_agent(self, name: str) -> Any | None:
        return self.agents.get(name)

    def get_available_agents(self) -> list[str]:
        return list(self.agents.keys())

    def route_query(self, intent: str) -> str:
        routing_map = {
            "kpi_query": "analytics_agent",
            "revenue_analysis": "analytics_agent",
            "sales_analysis": "analytics_agent",
            "forecast": "forecast_agent",
            "prediction": "forecast_agent",
            "dashboard_summary": "dashboard_agent",
            "root_cause": "root_cause_agent",
            "recommendation": "analytics_agent",
            "executive_summary": "executive_summary_agent",
            "report_generation": "analytics_agent",
        }
        return routing_map.get(intent, "analytics_agent")
