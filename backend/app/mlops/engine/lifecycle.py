"""MLOps model lifecycle state machine.

Governs valid transitions between model statuses:
  draft -> registered -> staging -> production -> archived -> retired

Also handles version promotion and rollback logic.
"""

from __future__ import annotations

from app.core.logging import get_logger

log = get_logger("mlops.lifecycle")

# Valid status transitions for models
VALID_MODEL_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"registered", "archived"},
    "registered": {"staging", "archived", "draft"},
    "staging": {"production", "registered", "archived"},
    "production": {"staging", "archived"},
    "archived": {"draft", "registered"},
    "retired": set(),
}

# Valid version status transitions
VALID_VERSION_TRANSITIONS: dict[str, set[str]] = {
    "created": {"validated", "staged", "archived"},
    "validated": {"staged", "archived"},
    "staged": {"production", "archived", "validated"},
    "production": {"staged", "archived"},
    "archived": {"created"},
    "retired": set(),
}

# Valid deployment status transitions
VALID_DEPLOYMENT_TRANSITIONS: dict[str, set[str]] = {
    "deploying": {"active", "failed"},
    "active": {"stopped", "rolled_back"},
    "failed": {"deploying", "stopped"},
    "stopped": {"deploying"},
    "rolled_back": {"deploying"},
}


class LifecycleError(Exception):
    """Raised when an invalid lifecycle transition is attempted."""

    def __init__(self, current: str, target: str, entity: str = "model"):
        self.current = current
        self.target = target
        self.entity = entity
        super().__init__(f"Cannot transition {entity} from '{current}' to '{target}'")


def validate_model_transition(current_status: str, target_status: str) -> bool:
    """Validate whether a model status transition is allowed."""
    valid = VALID_MODEL_TRANSITIONS.get(current_status, set())
    if target_status not in valid:
        log.warning(
            "invalid_model_transition",
            current=current_status,
            target=target_status,
            valid_targets=sorted(valid),
        )
        raise LifecycleError(current_status, target_status, "model")
    return True


def validate_version_transition(current_status: str, target_status: str) -> bool:
    """Validate whether a version status transition is allowed."""
    valid = VALID_VERSION_TRANSITIONS.get(current_status, set())
    if target_status not in valid:
        log.warning(
            "invalid_version_transition",
            current=current_status,
            target=target_status,
            valid_targets=sorted(valid),
        )
        raise LifecycleError(current_status, target_status, "version")
    return True


def validate_deployment_transition(current_status: str, target_status: str) -> bool:
    """Validate whether a deployment status transition is allowed."""
    valid = VALID_DEPLOYMENT_TRANSITIONS.get(current_status, set())
    if target_status not in valid:
        log.warning(
            "invalid_deployment_transition",
            current=current_status,
            target=target_status,
            valid_targets=sorted(valid),
        )
        raise LifecycleError(current_status, target_status, "deployment")
    return True


def can_promote_to_production(
    version_status: str, has_evaluation: bool, has_artifact: bool
) -> tuple[bool, list[str]]:
    """Check if a model version can be promoted to production.

    Returns (allowed, list of blocking reasons).
    """
    blockers: list[str] = []

    if version_status not in ("validated", "staged"):
        blockers.append(f"Version status must be 'validated' or 'staged', got '{version_status}'")

    if not has_artifact:
        blockers.append("Model artifact is missing")

    if not has_evaluation:
        blockers.append("Model has not been evaluated")

    allowed = len(blockers) == 0
    return allowed, blockers


def get_lifecycle_summary(
    model_status: str, version_status: str | None, deployment_status: str | None
) -> dict:
    """Return a human-readable lifecycle summary."""
    return {
        "model_status": model_status,
        "version_status": version_status,
        "deployment_status": deployment_status,
        "is_production": model_status == "production" and deployment_status == "active",
        "next_actions": _suggest_actions(model_status, version_status, deployment_status),
    }


def _suggest_actions(
    model_status: str, version_status: str | None, deployment_status: str | None
) -> list[str]:
    """Suggest possible next actions based on current lifecycle state."""
    actions: list[str] = []

    if model_status == "draft":
        actions.append("Register model to begin lifecycle")
    elif model_status == "registered":
        actions.append("Create a version and train on a dataset")
        actions.append("Move to staging for validation")
    elif model_status == "staging":
        if version_status == "validated":
            actions.append("Promote to production")
        else:
            actions.append("Validate version before production promotion")
    elif model_status == "production":
        if deployment_status == "active":
            actions.append("Monitor for drift and degradation")
            actions.append("Train new version for improvement")
        else:
            actions.append("Deploy model to serve predictions")

    return actions
