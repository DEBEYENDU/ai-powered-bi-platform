"""Observability and monitoring for AI Business Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta


class AIMetric(BaseModel):
    name: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = Field(default_factory=dict)
    unit: str = ""


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    model: str = ""


class LatencyMetric(BaseModel):
    operation: str
    latency_ms: float
    success: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AIMonitor:
    """Monitors AI assistant performance and metrics."""

    def __init__(self) -> None:
        self._metrics: List[AIMetric] = []
        self._token_usage: List[TokenUsage] = []
        self._latency_metrics: List[LatencyMetric] = []
        self._tool_calls: List[Dict[str, Any]] = []
        self._failures: List[Dict[str, Any]] = []

    def record_metric(self, metric: AIMetric) -> None:
        self._metrics.append(metric)

    def record_token_usage(
        self, prompt_tokens: int, completion_tokens: int,
        model: str, estimated_cost: float = 0.0
    ) -> None:
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=estimated_cost,
            model=model,
        )
        self._token_usage.append(usage)

    def record_latency(
        self, operation: str, latency_ms: float, success: bool
    ) -> None:
        self._latency_metrics.append(LatencyMetric(
            operation=operation, latency_ms=latency_ms, success=success,
        ))

    def record_tool_call(
        self, tool_name: str, success: bool,
        execution_time_ms: float, error: Optional[str] = None
    ) -> None:
        self._tool_calls.append({
            "tool": tool_name,
            "success": success,
            "execution_time_ms": execution_time_ms,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def record_failure(
        self, operation: str, error: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        self._failures.append({
            "operation": operation,
            "error": error,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_dashboard(self) -> Dict[str, Any]:
        avg_latency = (
            sum(m.latency_ms for m in self._latency_metrics) / len(self._latency_metrics)
            if self._latency_metrics else 0.0
        )
        success_rate = (
            sum(1 for m in self._latency_metrics if m.success) / len(self._latency_metrics)
            if self._latency_metrics else 0.0
        )
        total_tokens = sum(
            t.total_tokens for t in self._token_usage
        )
        total_cost = sum(
            t.estimated_cost for t in self._token_usage
        )
        return {
            "total_requests": len(self._latency_metrics),
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": round(success_rate, 4),
            "total_tokens": total_tokens,
            "total_estimated_cost": round(total_cost, 4),
            "total_tool_calls": len(self._tool_calls),
            "total_failures": len(self._failures),
            "hallucination_rate": self._calculate_hallucination_rate(),
        }

    def get_tool_metrics(self) -> Dict[str, Dict[str, Any]]:
        tool_stats: Dict[str, Dict[str, Any]] = {}
        for call in self._tool_calls:
            tool = call["tool"]
            if tool not in tool_stats:
                tool_stats[tool] = {"calls": 0, "successes": 0, "total_time": 0.0}
            tool_stats[tool]["calls"] += 1
            if call["success"]:
                tool_stats[tool]["successes"] += 1
            tool_stats[tool]["total_time"] += call["execution_time_ms"]
        return tool_stats

    def _calculate_hallucination_rate(self) -> float:
        total = len(self._token_usage)
        if total == 0:
            return 0.0
        return 0.0

    def generate_report(
        self, period: str = "last_24_hours"
    ) -> Dict[str, Any]:
        return {
            "period": period,
            "metrics": self.get_dashboard(),
            "generated_at": datetime.utcnow().isoformat(),
        }
