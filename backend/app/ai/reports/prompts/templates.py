"""LLM prompt templates for the AI Report Generator."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a senior business analyst and report writer embedded in an AI-Powered
Business Intelligence platform.  You generate professional, data-driven
business reports.  Always ground every statement in the data provided.
Use clear, concise, professional language suitable for C-suite executives.
Structure your output with headings, bullet points, and numbered lists."""

# ---------------------------------------------------------------------------
# Report generation (main)
# ---------------------------------------------------------------------------

REPORT_GENERATION_PROMPT = """\
Generate a professional business report based on the following request.

USER REQUEST: {prompt}

REPORT TYPE: {report_type}

DATA CONTEXT:
{data_context}

{kpis_context}

{chart_context}

{trend_context}

TASK:
Produce a complete report with the following sections.  Return valid JSON.

{{
  "title": "Report Title",
  "executive_summary": "2-3 paragraph executive summary",
  "sections": [
    {{
      "title": "Section Title",
      "content": "Section content with markdown formatting",
      "section_type": "analysis"
    }}
  ],
  "kpis": [
    {{
      "name": "KPI Name",
      "value": 12345,
      "unit": "$",
      "change_pct": 12.5,
      "trend": "up",
      "target": 15000,
      "description": "Brief description"
    }}
  ],
  "insights": [
    {{
      "title": "Insight Title",
      "description": "Detailed insight",
      "insight_type": "positive_trend",
      "metric": "revenue",
      "change_pct": 14.2,
      "confidence": "high"
    }}
  ],
  "risks": [
    {{
      "title": "Risk Title",
      "description": "Risk description",
      "severity": "high",
      "likelihood": "medium",
      "mitigation": "Suggested mitigation"
    }}
  ],
  "recommendations": [
    {{
      "title": "Recommendation Title",
      "description": "Detailed recommendation",
      "priority": "high",
      "category": "operations",
      "expected_impact": "Expected impact description",
      "confidence": "high"
    }}
  ]
}}"""

# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

EXECUTIVE_SUMMARY_PROMPT = """\
Generate an executive summary for the following report data.

REPORT: {report_type}
DATA:
{data_context}

TASK:
Write a 2-3 paragraph executive summary covering:
1. Overview of business performance
2. Key achievements and highlights
3. Major risks and concerns
4. Strategic outlook and confidence level

Tone: professional, concise, action-oriented."""

# ---------------------------------------------------------------------------
# Section-specific prompts
# ---------------------------------------------------------------------------

SECTION_PROMPTS: dict[str, str] = {
    "financial_analysis": """\
Analyse the following financial data and produce a detailed section.

DATA:
{data_context}

Include: Revenue, margins, costs, cash flow analysis, budget variance.""",

    "sales_analysis": """\
Analyse the following sales data and produce a detailed section.

DATA:
{data_context}

Include: Pipeline health, conversion rates, regional performance, top/bottom performers.""",

    "marketing_analysis": """\
Analyse the following marketing data and produce a detailed section.

DATA:
{data_context}

Include: Campaign performance, CAC, channel effectiveness, ROI.""",

    "customer_analysis": """\
Analyse the following customer data and produce a detailed section.

DATA:
{data_context}

Include: Segments, retention, churn, lifetime value, satisfaction.""",

    "operations_analysis": """\
Analyse the following operations data and produce a detailed section.

DATA:
{data_context}

Include: Efficiency metrics, throughput, quality, bottlenecks.""",

    "hr_analysis": """\
Analyse the following HR data and produce a detailed section.

DATA:
{data_context}

Include: Headcount, turnover, hiring pipeline, satisfaction, productivity.""",

    "forecast_section": """\
Generate a forecast section based on the following trends.

DATA:
{data_context}

Include: Predicted values, confidence intervals, key assumptions.""",

    "risk_analysis": """\
Identify and analyse business risks from the following data.

DATA:
{data_context}

For each risk: title, description, severity, likelihood, mitigation strategy.""",

    "recommendations_section": """\
Generate actionable recommendations based on the following analysis.

DATA:
{data_context}

For each: title, description, priority, category, expected impact, confidence."""
}

# ---------------------------------------------------------------------------
# Follow-up Q&A
# ---------------------------------------------------------------------------

FOLLOWUP_PROMPT = """\
You are a business analyst answering a follow-up question about a generated report.

REPORT CONTENT:
{report_context}

QUESTION: {question}

TASK:
Answer the question using the report data.  Provide:
1. A clear, concise answer
2. Supporting evidence from the report
3. Confidence level (low/medium/high)"""

# ---------------------------------------------------------------------------
# Format-specific summaries
# ---------------------------------------------------------------------------

PDF_PROMPT = """\
Format the following report content as a professional PDF document structure.
Use markdown-compatible formatting with clear headings, lists, and tables.

CONTENT:
{content}"""

DOCX_PROMPT = """\
Prepare the following report content for Word document export.
Structure with clear headings (H1, H2, H3), bullet points, and tables.

CONTENT:
{content}"""

PPTX_PROMPT = """\
Prepare the following report content as presentation slides.
For each slide, provide: title, 3-5 bullet points, speaker notes.

CONTENT:
{content}"""

EXCEL_PROMPT = """\
Prepare the following report data as structured tables for Excel export.
Specify columns, data types, and any aggregations needed.

CONTENT:
{content}"""
