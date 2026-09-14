"""Data classification service."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.governance.models.policy import DataClassification

log = get_logger("governance.classification")

CLASSIFICATION_LEVELS = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "RESTRICTED": 3}


class ClassificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def classify_resource(
        self, data: dict[str, Any], organization_id: str, classified_by: str = ""
    ) -> DataClassification:
        classification = DataClassification(
            organization_id=organization_id,
            resource_type=data["resource_type"],
            resource_id=data["resource_id"],
            classification=data.get("classification", "INTERNAL"),
            sensitivity_tags=data.get("sensitivity_tags", []),
            classified_by=classified_by,
        )
        self.db.add(classification)
        self.db.commit()
        self.db.refresh(classification)
        log.info(
            "resource_classified",
            resource_type=classification.resource_type,
            classification=classification.classification,
        )
        return classification

    def get_classification(
        self, resource_type: str, resource_id: str, organization_id: str
    ) -> DataClassification | None:
        stmt = select(DataClassification).where(
            DataClassification.resource_type == resource_type,
            DataClassification.resource_id == resource_id,
            DataClassification.organization_id == organization_id,
        )
        return self.db.scalars(stmt).first()

    def list_classifications(
        self, organization_id: str, resource_type: str | None = None
    ) -> list[DataClassification]:
        stmt = select(DataClassification).where(
            DataClassification.organization_id == organization_id
        )
        if resource_type:
            stmt = stmt.where(DataClassification.resource_type == resource_type)
        return list(self.db.scalars(stmt.all()))

    def can_export(
        self, resource_type: str, resource_id: str, organization_id: str
    ) -> tuple[bool, str]:
        cls = self.get_classification(resource_type, resource_id, organization_id)
        if cls and cls.classification == "RESTRICTED":
            return False, "Resource is RESTRICTED — export requires elevated approval"
        return True, ""

    def can_use_in_ai(
        self, resource_type: str, resource_id: str, organization_id: str
    ) -> tuple[bool, str]:
        cls = self.get_classification(resource_type, resource_id, organization_id)
        if cls and cls.classification == "RESTRICTED":
            return False, "Resource is RESTRICTED — AI processing not permitted"
        if cls and cls.classification == "CONFIDENTIAL":
            return True, "Resource is CONFIDENTIAL — AI processing logged"
        return True, ""
