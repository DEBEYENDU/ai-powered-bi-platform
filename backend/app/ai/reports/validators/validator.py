"""Validate report generation requests and inputs."""

from __future__ import annotations

from typing import Any

ALLOWED_REPORT_TYPES = {
    "executive",
    "sales",
    "marketing",
    "finance",
    "operations",
    "customer",
    "inventory",
    "hr",
    "manufacturing",
    "healthcare",
    "retail",
    "custom",
}

ALLOWED_EXPORT_FORMATS = {"pdf", "docx", "pptx", "xlsx", "csv", "json", "markdown", "html"}

ALLOWED_SCHEDULE_FREQUENCIES = {"daily", "weekly", "monthly", "quarterly", "yearly", "cron"}

BLOCKED_SQL_PATTERNS = {
    "DROP",
    "DELETE",
    "TRUNCATE",
    "ALTER",
    "INSERT",
    "UPDATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
}

MAX_PROMPT_LENGTH = 10000
MAX_SECTIONS = 50
MAX_FORMATS_PER_REQUEST = 8


def validate_report_type(report_type: str) -> str | None:
    """Return error message if report_type is invalid, else None."""
    if report_type.lower() not in ALLOWED_REPORT_TYPES:
        return f"Invalid report type '{report_type}'. Allowed: {sorted(ALLOWED_REPORT_TYPES)}"
    return None


def validate_export_format(fmt: str) -> str | None:
    """Return error message if format is invalid."""
    if fmt.lower() not in ALLOWED_EXPORT_FORMATS:
        return f"Invalid format '{fmt}'. Allowed: {sorted(ALLOWED_EXPORT_FORMATS)}"
    return None


def validate_prompt(prompt: str) -> str | None:
    """Validate report generation prompt."""
    if not prompt or not prompt.strip():
        return "Prompt cannot be empty"
    if len(prompt) > MAX_PROMPT_LENGTH:
        return f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"
    return None


def validate_branding(branding: dict[str, Any]) -> str | None:
    """Validate branding configuration."""
    allowed_keys = {
        "logo",
        "colors",
        "font",
        "page_size",
        "orientation",
        "header",
        "footer",
        "watermark",
    }
    unknown = set(branding.keys()) - allowed_keys
    if unknown:
        return f"Unknown branding options: {sorted(unknown)}"

    colors = branding.get("colors", {})
    if colors:
        for key, val in colors.items():
            if isinstance(val, str) and not val.startswith("#"):
                return f"Color '{key}' must be a hex value starting with #"

    orientation = branding.get("orientation", "")
    if orientation and orientation not in ("portrait", "landscape"):
        return f"Invalid orientation '{orientation}'. Use 'portrait' or 'landscape'"

    return None


def validate_schedule(schedule: dict[str, Any]) -> str | None:
    """Validate scheduling configuration."""
    freq = schedule.get("frequency", "")
    if freq and freq not in ALLOWED_SCHEDULE_FREQUENCIES:
        return f"Invalid frequency '{freq}'. Allowed: {sorted(ALLOWED_SCHEDULE_FREQUENCIES)}"

    if freq == "cron":
        cron = schedule.get("cron_expression", "")
        if not cron:
            return "Cron expression required when frequency is 'cron'"
        parts = cron.split()
        if len(parts) not in (5, 6):
            return "Cron expression must have 5 or 6 fields"

    recipients = schedule.get("recipients", [])
    if not isinstance(recipients, list):
        return "Recipients must be a list"

    return None


def validate_sections(sections: list[str]) -> str | None:
    """Validate section list."""
    if len(sections) > MAX_SECTIONS:
        return f"Too many sections ({len(sections)}). Maximum is {MAX_SECTIONS}"
    return None


def validate_formats(formats: list[str]) -> str | None:
    """Validate format list."""
    if len(formats) > MAX_FORMATS_PER_REQUEST:
        return f"Too many formats ({len(formats)}). Maximum is {MAX_FORMATS_PER_REQUEST}"
    for fmt in formats:
        err = validate_export_format(fmt)
        if err:
            return err
    return None


def validate_all(
    prompt: str,
    report_type: str = "custom",
    formats: list[str] | None = None,
    branding: dict[str, Any] | None = None,
    schedule: dict[str, Any] | None = None,
    sections: list[str] | None = None,
) -> str | None:
    """Run all validations, return first error or None."""
    err = validate_prompt(prompt)
    if err:
        return err
    err = validate_report_type(report_type)
    if err:
        return err
    if formats:
        err = validate_formats(formats)
        if err:
            return err
    if branding:
        err = validate_branding(branding)
        if err:
            return err
    if schedule:
        err = validate_schedule(schedule)
        if err:
            return err
    if sections:
        err = validate_sections(sections)
        if err:
            return err
    return None
