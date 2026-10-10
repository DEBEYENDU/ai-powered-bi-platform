"""Persistent registry for uploaded datasets (``de_datasets`` table).

Every upload is recorded with its organization and owner so that listing is
org-scoped and every downstream operation (profile, clean, transform, chat,
export) can be checked against the caller's tenant. The storage directory on
its own carries no ownership information, so it is never used to answer
"which datasets exist".
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.data_engineering.models import DatasetRecord


def _as_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _same_org(a: object, b: object) -> bool:
    return _as_uuid(a) is not None and _as_uuid(a) == _as_uuid(b)


def register_dataset(
    db: Session,
    *,
    dataset_id: str,
    organization_id: str,
    owner_id: str,
    name: str,
    description: str = "",
    source_type: str = "csv",
    storage_path: str = "",
    row_count: int = 0,
    column_count: int = 0,
    file_size: int = 0,
    status: str = "ready",
    schema_info: dict | None = None,
) -> DatasetRecord:
    """Persist dataset metadata for an uploaded dataset.

    Raises ``ValueError`` when the organization or owner is not a valid UUID
    (the ``de_datasets`` columns are UUIDs — callers surface the message to
    the client instead of letting the database reject the insert).
    """
    rid = _as_uuid(dataset_id)
    if rid is None:
        raise ValueError(f"Invalid dataset id: {dataset_id!r}")
    if _as_uuid(organization_id) is None:
        raise ValueError("Invalid organization id for dataset storage")
    if _as_uuid(owner_id) is None:
        raise ValueError("Invalid owner id for dataset storage")

    record = DatasetRecord(
        id=rid,
        organization_id=uuid.UUID(str(organization_id)),
        owner_id=uuid.UUID(str(owner_id)),
        name=name,
        description=description,
        source_type=source_type,
        storage_path=storage_path,
        row_count=row_count,
        column_count=column_count,
        file_size=file_size,
        status=status,
        schema_info=schema_info or {},
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_datasets(db: Session, organization_id: str) -> list[DatasetRecord]:
    """Return live datasets belonging to the organization."""
    org = _as_uuid(organization_id)
    if org is None:
        return []
    stmt = (
        select(DatasetRecord)
        .where(DatasetRecord.organization_id == org)
        .where(DatasetRecord.deleted_at.is_(None))
        .order_by(DatasetRecord.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def resolve_record(
    db: Session, organization_id: object, dataset_id: str
) -> DatasetRecord | None:
    """Find the dataset record for ``dataset_id`` inside the caller's org.

    Derived outputs (``<uuid>_clean``, ``<uuid>_t``) are written as files but
    do not get their own record, so they resolve through their base dataset.
    Returns ``None`` for unknown ids and for datasets owned by another org —
    callers answer with the same "not found" response for both.
    """
    org = _as_uuid(organization_id)
    if org is None:
        return None

    rid = _as_uuid(dataset_id)
    if rid is None and isinstance(dataset_id, str) and "_" in dataset_id:
        rid = _as_uuid(dataset_id.split("_", 1)[0])
    if rid is None:
        return None

    record = db.get(DatasetRecord, rid)
    if record is None or record.deleted_at is not None:
        return None
    if record.organization_id != org:
        return None
    return record


def owns_dataset(db: Session, organization_id: object, dataset_id: str) -> bool:
    return resolve_record(db, organization_id, dataset_id) is not None
