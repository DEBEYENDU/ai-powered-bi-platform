"""Tenant-aware storage — isolates file storage per organization."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class TenantStorage:
    """Provides isolated storage paths per tenant.
    
    Directory structure:
    storage/
      tenants/
        {tenant_id}/
          datasets/
          reports/
          exports/
          uploads/
          artifacts/
          knowledge/
    """

    def __init__(self) -> None:
        self._base = get_settings().storage_dir

    def _tenant_root(self, tenant_id: str) -> Path:
        path = self._base / "tenants" / tenant_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_path(self, tenant_id: str, category: str, *parts: str) -> Path:
        path = self._tenant_root(tenant_id) / category
        for part in parts:
            path = path / part
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def get_dataset_path(self, tenant_id: str, dataset_id: str, filename: str) -> Path:
        return self.get_path(tenant_id, "datasets", dataset_id, filename)

    def get_report_path(self, tenant_id: str, report_id: str, filename: str) -> Path:
        return self.get_path(tenant_id, "reports", report_id, filename)

    def get_export_path(self, tenant_id: str, filename: str) -> Path:
        return self.get_path(tenant_id, "exports", filename)

    def get_upload_path(self, tenant_id: str, filename: str) -> Path:
        return self.get_path(tenant_id, "uploads", filename)

    def get_artifact_path(self, tenant_id: str, artifact_id: str, filename: str) -> Path:
        return self.get_path(tenant_id, "artifacts", artifact_id, filename)

    def get_knowledge_path(self, tenant_id: str, doc_id: str) -> Path:
        return self.get_path(tenant_id, "knowledge", doc_id)

    def get_tenant_size(self, tenant_id: str) -> int:
        root = self._tenant_root(tenant_id)
        total = 0
        if root.exists():
            for f in root.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        return total

    def delete_tenant_storage(self, tenant_id: str) -> bool:
        root = self._tenant_root(tenant_id)
        if root.exists():
            shutil.rmtree(root)
            log.info("tenant_storage_deleted", tenant_id=tenant_id)
            return True
        return False
