"""LLM prompt templates used by the Business Analyst engines."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a senior business analyst and data scientist embedded in an
AI-Powered Business Intelligence platform.  You analyse dashboard data and
produce actionable business insights.  Always ground every statement in the
data provided.  Respond in concise, professional language suitable for
C-suite executives.  Use bullet points where appropriate."""

# ---------------------------------------------------------------------------
# Insight generation
# ---------------------------------------------------------------------------

INSIGHT_PROMPT = """\
Analyse the following dashboard data and produce business insights.

DATA:
{data_context}

{comparison_context}

TASK:
Identify the most important business insights.  For each insight:
1. Classify it as one of: positive_trend, negative_trend, highest_growth,
   lowest_growth, top_product, worst_product, regional_comparison,
   department_comparison, customer_segment, seasonality.
2. Provide a clear title and 1-2 sentence description.
3. List evidence from the data.
4. Assign confidence: low / medium / high.
5. Estimate the business impact.

Return a JSON array of insights.  Each element must have:
type, title, description, evidence (list), confidence, metric,
current_value, previous_value (or null), change_pct, impact."""

# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

ANOMALY_PROMPT = """\
Review the following data for anomalies, outliers, and data-quality issues.

DATA:
{data_context}

TASK:
Detect anomalies and classify each as: revenue_spike, revenue_drop,
unexpected_sales, outlier, missing_values, duplicate_records,
unusual_behavior, or performance_degradation.

For each anomaly provide: type, title, description, severity (low/medium/high),
metric, expected_value, actual_value, deviation_pct, confidence, evidence."""

# ---------------------------------------------------------------------------
# Root cause analysis
# ---------------------------------------------------------------------------

ROOT_CAUSE_PROMPT = """\
A business metric has changed.  Explain WHY.

CURRENT DATA:
{current_context}

PREVIOUS DATA:
{previous_context}

CHANGE SUMMARY:
{change_summary}

TASK:
Identify the top contributing factors.  For each factor provide:
- factor name
- contribution percentage (how much of the change it explains)
- explanation
- evidence from the data

Return a JSON array of root causes."""

# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

RECOMMENDATION_PROMPT = """\
Based on the following business analysis, generate actionable recommendations.

INSIGHTS:
{insights_context}

ANOMALIES:
{anomalies_context}

ROOT CAUSES:
{root_causes_context}

TASK:
Generate 3-7 business recommendations.  For each provide:
- title
- description
- category (operations / marketing / sales / finance / product / hr)
- priority (low / medium / high / critical)
- expected_impact
- evidence
- confidence
- business_logic
- action_items (list of concrete steps)

Return a JSON array of recommendations."""

# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

SUMMARY_PROMPTS: dict[str, str] = {
    "board_meeting": """\
Generate a board-meeting-ready executive summary of the following analysis.

ANALYSIS:
{analysis_context}

Tone: formal, strategic, high-level.  Focus on:
- Overall business health
- Key risks and opportunities
- Strategic recommendations
- Quarter/year performance vs targets""",
    "ceo": """\
Generate a CEO summary of the following analysis.

ANALYSIS:
{analysis_context}

Tone: concise, action-oriented.  Focus on:
- Top-line performance
- Critical decisions needed
- Growth trajectory
- Competitive position""",
    "finance": """\
Generate a finance-focused summary of the following analysis.

ANALYSIS:
{analysis_context}

Tone: precise, numbers-driven.  Focus on:
- Revenue, margin, and cost metrics
- Budget variance
- Cash flow implications
- Financial risks""",
    "sales": """\
Generate a sales-focused summary of the following analysis.

ANALYSIS:
{analysis_context}

Tone: energetic, performance-driven.  Focus on:
- Pipeline health
- Conversion rates
- Top and bottom performers
- Regional performance""",
    "marketing": """\
Generate a marketing-focused summary of the following analysis.

ANALYSIS:
{analysis_context}

Tone: creative, ROI-focused.  Focus on:
- Campaign performance
- Customer acquisition cost
- Channel effectiveness
- Brand metrics""",
    "operations": """\
Generate an operations-focused summary of the following analysis.

ANALYSIS:
{analysis_context}

Tone: efficiency-focused.  Focus on:
- Process efficiency
- Resource utilisation
- Quality metrics
- Bottlenecks and improvements""",
    "executive_brief": """\
Generate a concise executive brief of the following analysis.

ANALYSIS:
{analysis_context}

Tone: professional, balanced.  3-5 paragraphs covering:
1. Current state
2. Key findings
3. Risks and opportunities
4. Recommended actions""",
}

# ---------------------------------------------------------------------------
# Forecast narrative
# ---------------------------------------------------------------------------

FORECAST_PROMPT = """\
A time-series forecast has been computed.  Provide a business narrative.

METRIC: {metric}
HORIZON: {horizon_days} days
TREND: {trend}
SEASONALITY: {seasonality}
DATA POINTS:
{forecast_points}

TASK:
Interpret the forecast in business terms.  Explain:
1. What the trend means for the business
2. Expected range of outcomes
3. Key risks to the forecast
4. Confidence level and why"""

# ---------------------------------------------------------------------------
# Follow-up Q&A
# ---------------------------------------------------------------------------

FOLLOWUP_PROMPT = """\
You are a business analyst answering a follow-up question about a dashboard.

DASHBOARD DATA:
{data_context}

PREVIOUS ANALYSIS:
{analysis_context}

QUESTION: {question}

TASK:
Answer the question using the data and analysis above.  Provide:
1. A clear, concise answer
2. Supporting evidence from the data
3. Confidence level (low/medium/high)
4. Any related insights the user should know about"""

# ---------------------------------------------------------------------------
# Chart explanation
# ---------------------------------------------------------------------------

CHART_EXPLAIN_PROMPT = """\
Explain the following chart/widget in business terms.

CHART:
Title: {title}
Type: {chart_type}
Data: {data_summary}

TASK:
Provide:
1. "meaning" — What does this chart show? (1-2 sentences)
2. "action" — What should the viewer do about it? (1-2 sentences)
3. "importance" — How important is this metric? (low/medium/high with reason)
4. "confidence" — How confident are you in this interpretation?"""
