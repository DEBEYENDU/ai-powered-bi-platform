"""Safety and content moderation for AI Business Assistant."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class SafetyCheckResult(BaseModel):
    is_safe: bool
    blocked: bool = False
    risk_level: str = "low"
    flagged_patterns: list[str] = Field(default_factory=list)
    sanitized_text: str = ""


class SafetyChecker:
    """Checks queries for safety and malicious content."""

    INJECTION_PATTERNS = [
        r"(?i)drop\s+table",
        r"(?i)delete\s+from",
        r"(?i)insert\s+into",
        r"(?i)update\s+\w+\s+set",
        r"(?i)union\s+(all\s+)?select",
        r"(?i)1\s*=\s*1",
        r"(?i)'\s*or\s*'",
        r"(?i)exec\s*\(",
        r"(?i)eval\s*\(",
        r"(?i)os\.system",
        r"(?i)subprocess\.",
        r"(?i)bash\s+-c",
        r"(?i)/etc/passwd",
        r"(?i)\.\./\.\./",
        r"(?i)<script",
        r"(?i)javascript:",
        r"(?i)onerror\s*=",
        r"(?i)onload\s*=",
    ]

    MALICIOUS_KEYWORDS = [
        "hack",
        "exploit",
        "bypass",
        "crack",
        "inject",
        "sql injection",
        "xss",
        "csrf",
        "ddos",
    ]

    SENSITIVE_PATTERNS = [
        r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    ]

    def __init__(self) -> None:
        self._injection_regexes = [re.compile(p) for p in self.INJECTION_PATTERNS]
        self._sensitive_regexes = [re.compile(p) for p in self.SENSITIVE_PATTERNS]

    def is_safe(self, text: str) -> bool:
        text_lower = text.lower()
        for pattern in self._injection_regexes:
            if pattern.search(text):
                return False
        return all(keyword not in text_lower for keyword in self.MALICIOUS_KEYWORDS)

    def sanitize_input(self, text: str) -> str:
        sanitized = text.strip()
        for pattern in self.INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[removed]", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"[^\w\s.,?!:;'\"\-()[\]{}@#$%^&*]", "", sanitized)
        return sanitized[:4000]

    def check_safety(self, text: str) -> SafetyCheckResult:
        sanitized = self.sanitize_input(text)
        is_safe = self.is_safe(sanitized)
        flagged: list[str] = []
        risk_level = "low"

        for pattern in self._injection_regexes:
            if pattern.search(text):
                flagged.append(pattern.pattern[:50])
                risk_level = "high"

        for keyword in self.MALICIOUS_KEYWORDS:
            if keyword in text.lower():
                flagged.append(f"malicious_keyword: {keyword}")
                risk_level = "high"

        for sensitive_pattern in self._sensitive_regexes:
            if sensitive_pattern.search(text):
                flagged.append("sensitive_data_detected")
                risk_level = max(risk_level, "medium")

        return SafetyCheckResult(
            is_safe=is_safe,
            blocked=not is_safe,
            risk_level=risk_level,
            flagged_patterns=flagged,
            sanitized_text=sanitized,
        )
