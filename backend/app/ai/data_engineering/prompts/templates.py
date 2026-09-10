"""LLM prompt templates for data engineering tasks."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are a senior data engineer and data quality specialist embedded in an
AI-Powered Business Intelligence platform.  You analyse datasets, detect
quality issues, recommend cleaning operations, and generate transformations.
Always ground recommendations in the actual data statistics provided.
Respond with structured JSON when requested."""

# ---------------------------------------------------------------------------
# Dataset understanding
# ---------------------------------------------------------------------------

DATASET_UNDERSTANDING_PROMPT = """\
Analyse the following dataset profile and provide insights.

DATASET: {name}
ROWS: {row_count}
COLUMNS: {column_count}

COLUMN PROFILES:
{column_profiles}

TASK:
Provide:
1. What this dataset represents (business purpose)
2. Key observations about data quality
3. Likely primary keys and foreign keys
4. Column type inferences (dates, currencies, categories, etc.)
5. Potential issues to investigate
6. Top 3 recommended actions

Return JSON with keys: purpose, observations, keys, type_inferences, issues, recommendations."""

# ---------------------------------------------------------------------------
# Quality issues
# ---------------------------------------------------------------------------

QUALITY_ANALYSIS_PROMPT = """\
Analyse the following data quality results and provide recommendations.

QUALITY SCORES:
{quality_scores}

ISSUES FOUND:
{issues}

TASK:
For each issue, provide:
1. Root cause explanation
2. Business impact
3. Recommended fix with specific steps
4. Whether it can be auto-fixed

Return JSON array of recommendations."""

# ---------------------------------------------------------------------------
# Cleaning suggestions
# ---------------------------------------------------------------------------

CLEANING_PROMPT = """\
Review the following data issues and suggest cleaning operations.

COLUMN: {column}
CURRENT STATE:
{current_state}

STATISTICS:
{statistics}

TASK:
Suggest cleaning operations. For each:
1. transform_type: fill_missing, remove_duplicates, standardize, normalize_text, trim_spaces, convert_type
2. parameters: specific configuration
3. description: what it does
4. confidence: 0-1 how confident you are
5. auto_applicable: whether it can be applied without user confirmation

Return JSON array of cleaning suggestions."""

# ---------------------------------------------------------------------------
# Relationship discovery
# ---------------------------------------------------------------------------

RELATIONSHIP_PROMPT = """\
Analyse the following tables and discover relationships.

TABLES:
{table_info}

TASK:
Discover:
1. Foreign key relationships between tables
2. Join keys for combining tables
3. Which tables are dimensions vs facts
4. Whether the schema is star, snowflake, or denormalized
5. Recommended joins for analytics

Return JSON with: relationships, schema_type, join_recommendations."""

# ---------------------------------------------------------------------------
# Transformation recommendations
# ---------------------------------------------------------------------------

TRANSFORM_PROMPT = """\
Based on the following dataset analysis, recommend transformations.

DATASET:
{dataset_info}

USER GOAL: {goal}

TASK:
Recommend specific transformations to achieve the goal. For each:
1. transform_type
2. column(s) involved
3. parameters
4. expected outcome
5. order of execution

Return JSON array of transform steps."""

# ---------------------------------------------------------------------------
# Data chat
# ---------------------------------------------------------------------------

DATASET_CHAT_PROMPT = """\
You are a data analyst answering questions about a dataset.

DATASET: {name}
SCHEMA:
{schema}

PROFILE SUMMARY:
{profile_summary}

QUESTION: {question}

TASK:
Answer the question using the dataset metadata and profile.
Provide:
1. Clear answer
2. Supporting evidence from the data
3. Suggested follow-up actions if applicable"""

# ---------------------------------------------------------------------------
# Schema inference
# ---------------------------------------------------------------------------

SCHEMA_INFER_PROMPT = """\
Analyse the following columns and infer their semantic types.

COLUMNS:
{columns}

SAMPLE DATA:
{sample_data}

TASK:
For each column, infer:
1. Semantic type (id, name, email, phone, address, date, currency, category, boolean, measurement, text)
2. Business purpose
3. Data format pattern
4. Whether it's likely a primary/foreign key

Return JSON array with: column, semantic_type, purpose, format, key_likelihood."""
