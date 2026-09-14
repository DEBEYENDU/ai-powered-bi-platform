"""Pydantic schemas for enterprise governance."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class PolicyCreate(BaseModel):
    name: str
    description: str = ""
    resource: str
    action: str
    subject_type: str = "role"
    subject_id: str = ""
    effect: str = "ALLOW"
    conditions: dict[str, Any] = {}
    priority: int = 0
    enabled: bool = True


class PolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    effect: str | None = None
    conditions: dict[str, Any] | None = None
    priority: int | None = None
    enabled: bool | None = None


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    name: str
    description: str
    resource: str
    action: str
    subject_type: str
    subject_id: str
    effect: str
    conditions: dict[str, Any]
    priority: int
    enabled: bool
    created_by: str
    created_at: str
    updated_at: str


class ClassificationCreate(BaseModel):
    resource_type: str
    resource_id: str
    classification: str = "INTERNAL"
    sensitivity_tags: list[str] = []
    notes: str = ""


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    resource_type: str
    resource_id: str
    classification: str
    sensitivity_tags: list[str]
    classified_by: str
    classified_at: str
    notes: str


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    event_type: str
    severity: str
    actor_id: str
    actor_email: str
    resource_type: str
    resource_id: str
    action: str
    outcome: str
    details: dict[str, Any]
    source_ip: str
    request_id: str
    created_at: str


class SecuritySummary(BaseModel):
    total_events: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    period_hours: int


class RetentionPolicyCreate(BaseModel):
    name: str
    resource_type: str
    retention_days: int = 365
    auto_delete: bool = False


class RetentionPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    name: str
    resource_type: str
    retention_days: int
    auto_delete: bool
    legal_hold: bool
    enabled: bool
    created_at: str


class AuthorizationCheck(BaseModel):
    user_id: str
    organization_id: str
    action: str
    resource_type: str
    resource_id: str | None = None


class AuthorizationResult(BaseModel):
    allowed: bool
    reason: str = ""


class ShareCreate(BaseModel):
    resource_type: str
    resource_id: str
    share_type: str
    grantee_id: str
    permissions: list[str] = ["read"]
    expires_at: str | None = None


class ShareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    resource_type: str
    resource_id: str
    share_type: str
    grantee_id: str
    permissions: list[str]
    created_at: str
