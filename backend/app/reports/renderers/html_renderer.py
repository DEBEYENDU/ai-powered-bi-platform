"""HTML renderer for reports.

Produces a self-contained HTML document (inline CSS) from a BuiltReport.
HTML is the canonical intermediate format: PDF/PNG/SVG exporters render
from it when their optional dependencies are present.
"""

from __future__ import annotations

import html as html_lib
from typing import Any, Dict


def _esc(value: Any) -> str:
    return html_lib.escape(str(value) if value is not None else "")


def render_section(section: Dict[str, Any]) -> str:
    kind = section.get("kind", "text")
    title = _esc(section.get("title") or section.get("section_id", ""))
    data = section.get("data", {})
    payload = data.get("payload", data) if isinstance(data, dict) else data

    body = ""
    if kind in ("kpi",):
        body = f"<div class='kpi'><pre>{_esc(payload)}</pre></div>"
    elif kind in ("chart", "heatmap", "trend", "dashboard"):
        body = (
            "<div class='chart-placeholder'>"
            f"<p>Chart ({_esc(kind)}) – rendered by dashboard visualization engine</p>"
            f"<pre>{_esc(payload)}</pre></div>"
        )
    elif kind in ("table", "pivot"):
        body = f"<div class='table-wrap'><pre>{_esc(payload)}</pre></div>"
    elif kind in ("summary", "insights", "recommendations", "root_cause", "forecast_text"):
        text = payload.get("text", "") if isinstance(payload, dict) else payload
        body = f"<div class='ai-section'><p>{_esc(text)}</p></div>"
    elif kind == "toc":
        body = "<div class='toc'><p>Table of contents generated at render time.</p></div>"
    else:
        body = f"<div class='static'><pre>{_esc(payload)}</pre></div>"

    return f"<section class='report-section {kind}'><h2>{title}</h2>{body}</section>"


def render_html(report: Dict[str, Any], layout: Dict[str, Any] | None = None,
                theme_css: str = "") -> str:
    layout = layout or {}
    brand = layout.get("brand", {})
    company = _esc(brand.get("company", ""))
    title = _esc(report.get("title", "Report"))
    generated = _esc(str(report.get("generated_at", "")))
    sections = report.get("sections", [])
    header = layout.get("header", {}).get("rendered", title)
    footer = layout.get("footer", {}).get("rendered", "")

    sections_html = "\n".join(
        render_section(s if isinstance(s, dict) else s.dict()) for s in sections
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:Helvetica,Arial,sans-serif;margin:40px;color:#222}}
.report-header{{border-bottom:3px solid #1e3a5f;padding-bottom:12px;margin-bottom:24px}}
.report-section{{margin:24px 0;page-break-inside:avoid}}
.kpi pre,.table-wrap pre,.static pre,.chart-placeholder pre{{background:#f5f7fa;padding:12px;border-radius:6px;white-space:pre-wrap}}
.chart-placeholder{{border:1px dashed #888;padding:12px;border-radius:6px}}
.ai-section{{background:#f0f6ff;border-left:4px solid #1e3a5f;padding:12px}}
.report-footer{{margin-top:32px;border-top:1px solid #ccc;padding-top:8px;font-size:12px;color:#666}}
{theme_css}
</style></head>
<body>
<header class="report-header"><div>{company}</div><h1>{title}</h1>
<div class="meta">Generated: {generated} | {header}</div></header>
<main>{sections_html}</main>
<footer class="report-footer">{footer}</footer>
</body></html>"""
