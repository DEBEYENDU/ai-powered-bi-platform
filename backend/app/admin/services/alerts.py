"""Alert engine: configurable threshold rules evaluated over metrics.

Operators: >, <, >=, <=, ==, !=. Firing creates incidents; auto-resolve closes
them when the metric recovers. Notification dispatch is delegated to the
notifications service via an injected callback.
"""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

OPS = {">": operator.gt, "<": operator.lt, ">=": operator.ge,
       "<=": operator.le, "==": operator.eq, "!=": operator.ne}


class AlertService:
    def __init__(self, notify: Optional[Callable[[Dict[str, Any]], Any]] = None) -> None:
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._incidents: Dict[str, Dict[str, Any]] = {}
        self._notify = notify

    def create_rule(self, name: str, metric: str, threshold: float,
                    rule_operator: str = ">", window_seconds: int = 300,
                    severity: str = "warning") -> Dict[str, Any]:
        if rule_operator not in OPS:
            raise ValueError(f"Unknown operator '{rule_operator}'")
        rule = {"id": str(uuid4()), "name": name, "metric": metric,
                "operator": rule_operator, "threshold": threshold,
                "window_seconds": window_seconds, "severity": severity,
                "enabled": True, "created_at": datetime.utcnow().isoformat()}
        self._rules[rule["id"]] = rule
        return rule

    def list_rules(self) -> List[Dict[str, Any]]:
        return list(self._rules.values())

    def delete_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def set_enabled(self, rule_id: str, enabled: bool) -> Optional[Dict[str, Any]]:
        rule = self._rules.get(rule_id)
        if rule:
            rule["enabled"] = enabled
        return rule

    def evaluate(self, metric: str, value: float) -> List[Dict[str, Any]]:
        fired: List[Dict[str, Any]] = []
        for rule in self._rules.values():
            if not rule["enabled"] or rule["metric"] != metric:
                continue
            if OPS[rule["operator"]](value, rule["threshold"]):
                incident = self._fire(rule, value)
                fired.append(incident)
            else:
                self._auto_resolve(rule["id"])
        return fired

    def _fire(self, rule: Dict[str, Any], value: float) -> Dict[str, Any]:
        for incident in self._incidents.values():
            if incident["rule_id"] == rule["id"] and incident["status"] == "firing":
                incident["observed_value"] = value
                return incident
        incident = {"id": str(uuid4()), "rule_id": rule["id"], "metric": rule["metric"],
                    "observed_value": value, "severity": rule["severity"],
                    "status": "firing", "created_at": datetime.utcnow().isoformat(),
                    "resolved_at": None}
        self._incidents[incident["id"]] = incident
        if self._notify:
            try:
                self._notify(incident)
            except Exception:
                pass
        return incident

    def _auto_resolve(self, rule_id: str) -> None:
        for incident in self._incidents.values():
            if incident["rule_id"] == rule_id and incident["status"] in ("firing", "acknowledged"):
                incident["status"] = "resolved"
                incident["resolved_at"] = datetime.utcnow().isoformat()

    def incidents(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        items = list(self._incidents.values())
        if status:
            items = [i for i in items if i["status"] == status]
        return sorted(items, key=lambda i: i["created_at"], reverse=True)

    def acknowledge(self, incident_id: str) -> Optional[Dict[str, Any]]:
        incident = self._incidents.get(incident_id)
        if incident and incident["status"] == "firing":
            incident["status"] = "acknowledged"
        return incident
