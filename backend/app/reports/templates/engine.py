"""Template engine for reports.

Jinja2 is used when available; otherwise a safe ``{{ variable }}`` fallback
renderer handles plain templates so unit tests and minimal deployments work
without optional dependencies.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TemplateVersion(BaseModel):
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    version_number: int = 1
    layout: Dict[str, Any] = Field(default_factory=dict)
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    change_note: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReportTemplate(BaseModel):
    template_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    current_version: int = 1
    versions: List[TemplateVersion] = Field(default_factory=list)
    shared: bool = False

    def active_version(self) -> Optional[TemplateVersion]:
        for v in reversed(self.versions):
            if v.approved:
                return v
        return self.versions[-1] if self.versions else None


_DEFAULT_LAYOUT: Dict[str, Any] = {
    "orientation": "portrait",
    "page_size": "A4",
    "margins_mm": {"top": 20, "bottom": 20, "left": 15, "right": 15},
    "font_family": "Helvetica",
    "brand": {"company": "", "logo_path": "", "primary_color": "#1e3a5f"},
    "header": {"enabled": True, "template": "{{ title }}"},
    "footer": {"enabled": True, "template": "Page {{ page }} of {{ pages }}"},
    "watermark": "",
}


class TemplateEngine:
    """Manages templates: CRUD, versioning, approval, rendering."""

    def __init__(self) -> None:
        self._templates: Dict[str, ReportTemplate] = {}
        try:
            from jinja2 import Environment  # type: ignore

            self._jinja = Environment(autoescape=False)
            self._has_jinja = True
        except Exception:
            self._jinja = None
            self._has_jinja = False

    # -- CRUD / versioning --
    def create(self, name: str, description: str = "", layout: Optional[Dict[str, Any]] = None,
               sections: Optional[List[Dict[str, Any]]] = None, shared: bool = False) -> ReportTemplate:
        merged = copy.deepcopy(_DEFAULT_LAYOUT)
        merged.update(layout or {})
        tpl = ReportTemplate(name=name, description=description, shared=shared)
        tpl.versions.append(TemplateVersion(
            version_number=1, layout=merged, sections=list(sections or [])))
        self._templates[tpl.template_id] = tpl
        return tpl

    def update(self, template_id: str, layout: Optional[Dict[str, Any]] = None,
               sections: Optional[List[Dict[str, Any]]] = None,
               change_note: str = "") -> TemplateVersion:
        tpl = self._require(template_id)
        base = copy.deepcopy(tpl.versions[-1].layout)
        if layout:
            base.update(layout)
        version = TemplateVersion(
            version_number=tpl.current_version + 1,
            layout=base,
            sections=list(sections) if sections is not None else copy.deepcopy(tpl.versions[-1].sections),
            change_note=change_note,
        )
        tpl.versions.append(version)
        tpl.current_version = version.version_number
        return version

    def approve(self, template_id: str, version_number: int, approved_by: str) -> bool:
        tpl = self._require(template_id)
        for v in tpl.versions:
            if v.version_number == version_number:
                v.approved = True
                v.approved_by = approved_by
                v.approved_at = datetime.utcnow()
                return True
        return False

    def get(self, template_id: str) -> Optional[ReportTemplate]:
        return self._templates.get(template_id)

    def list(self, shared_only: bool = False) -> List[ReportTemplate]:
        tpls = list(self._templates.values())
        return [t for t in tpls if t.shared] if shared_only else tpls

    # -- rendering --
    def render_string(self, template: str, variables: Dict[str, Any]) -> str:
        if self._has_jinja and self._jinja is not None:
            return self._jinja.from_string(template).render(**variables)
        def _repl(m: re.Match) -> str:
            key = m.group(1).strip()
            return str(variables.get(key, m.group(0)))
        return re.sub(r"\{\{\s*(.*?)\s*\}\}", _repl, template)

    def apply_layout(self, template_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        tpl = self._require(template_id)
        active = tpl.active_version()
        layout = copy.deepcopy(active.layout if active else _DEFAULT_LAYOUT)
        header = layout.get("header", {})
        footer = layout.get("footer", {})
        if isinstance(header.get("template"), str):
            header["rendered"] = self.render_string(header["template"], variables)
        if isinstance(footer.get("template"), str):
            footer["rendered"] = self.render_string(footer["template"], variables)
        return layout

    def _require(self, template_id: str) -> ReportTemplate:
        tpl = self._templates.get(template_id)
        if tpl is None:
            raise ValueError(f"Template '{template_id}' not found")
        return tpl
