"""Feature flag evaluation: boolean, percentage, org/user/env rollouts,
scheduled windows, dependencies, kill switches. Every change bumps version
and appends to history for audit.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional


class FeatureFlagService:
    def __init__(self) -> None:
        self._flags: Dict[str, Dict[str, Any]] = {}
        self._history: List[Dict[str, Any]] = []

    def create(self, key: str, description: str = "", flag_type: str = "boolean",
               default_value: Optional[Dict[str, Any]] = None,
               rules: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if key in self._flags:
            raise ValueError(f"Flag '{key}' already exists")
        flag = {"key": key, "description": description, "flag_type": flag_type,
                "default_value": default_value or {"enabled": False},
                "rules": rules or [], "enabled": True, "version": 1,
                "killed": False}
        self._flags[key] = flag
        self._log(key, "created", 1)
        return flag

    def update(self, key: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        flag = self._require(key)
        flag.update({k: v for k, v in patch.items() if k in
                     ("description", "default_value", "rules", "enabled")})
        flag["version"] += 1
        self._log(key, "updated", flag["version"])
        return flag

    def kill(self, key: str) -> Dict[str, Any]:
        flag = self._require(key)
        flag["killed"] = True
        flag["version"] += 1
        self._log(key, "killed", flag["version"])
        return flag

    def delete(self, key: str) -> bool:
        if key not in self._flags:
            return False
        del self._flags[key]
        self._log(key, "deleted", 0)
        return True

    def evaluate(self, key: str, user_id: Optional[str] = None,
                 organization_id: Optional[str] = None,
                 environment: str = "production",
                 now: Optional[datetime] = None) -> Dict[str, Any]:
        flag = self._require(key)
        if flag["killed"] or not flag["enabled"]:
            return {"key": key, "enabled": False, "reason": "killed_or_disabled"}
        moment = now or datetime.utcnow()
        for rule in flag["rules"]:
            if self._rule_matches(rule, user_id, organization_id, environment, moment, key):
                return {"key": key, "enabled": bool(rule.get("enabled", True)),
                        "reason": f"rule:{rule.get('name', 'unnamed')}"}
        return {"key": key, "enabled": bool(flag["default_value"].get("enabled", False)),
                "reason": "default"}

    def _rule_matches(self, rule: Dict[str, Any], user_id: Optional[str],
                      organization_id: Optional[str], environment: str,
                      moment: datetime, flag_key: str) -> bool:
        if rule.get("environment") and rule["environment"] != environment:
            return False
        window = rule.get("schedule", {})
        if window.get("starts_at") and moment < datetime.fromisoformat(window["starts_at"]):
            return False
        if window.get("ends_at") and moment > datetime.fromisoformat(window["ends_at"]):
            return False
        if rule.get("depends_on"):
            dep = self._flags.get(rule["depends_on"])
            if not dep or dep.get("killed"):
                return False
        orgs = rule.get("organizations", [])
        if orgs and organization_id not in orgs:
            return False
        users = rule.get("users", [])
        if users and user_id not in users:
            return False
        pct = rule.get("percentage")
        if pct is not None:
            bucket = int(hashlib.sha256(
                f"{flag_key}:{user_id or organization_id or 'anon'}".encode()
            ).hexdigest(), 16) % 100
            return bucket < int(pct)
        return True

    def list(self) -> List[Dict[str, Any]]:
        return list(self._flags.values())

    def history(self, key: Optional[str] = None) -> List[Dict[str, Any]]:
        return [h for h in self._history if key is None or h["key"] == key]

    def _require(self, key: str) -> Dict[str, Any]:
        flag = self._flags.get(key)
        if flag is None:
            raise ValueError(f"Flag '{key}' not found")
        return flag

    def _log(self, key: str, action: str, version: int) -> None:
        self._history.append({"key": key, "action": action, "version": version,
                              "at": datetime.utcnow().isoformat()})
