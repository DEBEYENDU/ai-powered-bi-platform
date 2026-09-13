"""Built-in data quality validator — checks common issues without requiring
external rule definitions.  Also supports user-supplied rule dicts."""

from __future__ import annotations

import re
import uuid
from typing import Any

import numpy as np
import pandas as pd

from app.ai.data_engineering.schemas import QualityIssue, QualityScore


def _iid() -> str:
    return str(uuid.uuid4())[:8]


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_dataset(
    df: pd.DataFrame,
    rules: list[dict[str, Any]] | None = None,
) -> tuple[list[QualityIssue], QualityScore]:
    """Run all built-in checks plus any user-supplied rules.

    Returns ``(issues, quality_score)``.
    """
    issues: list[QualityIssue] = []

    # ---- Built-in checks ----

    total_rows = len(df)
    if total_rows == 0:
        return issues, QualityScore(
            overall=100,
            completeness=100,
            consistency=100,
            accuracy=100,
            uniqueness=100,
            validity=100,
            timeliness=100,
        )

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        null_count = int(series.isna().sum())
        null_pct = null_count / total_rows * 100

        # 1. Missing values
        if null_pct > 5:
            severity = "critical" if null_pct > 30 else "high" if null_pct > 15 else "medium"
            issues.append(
                QualityIssue(
                    id=_iid(),
                    dimension="completeness",
                    severity=severity,
                    column=col,
                    issue_type="missing_values",
                    description=f"{col}: {null_count} missing values ({null_pct:.1f}%)",
                    affected_rows=null_count,
                    affected_pct=round(null_pct, 2),
                    suggestion="Fill missing values or drop column if mostly empty",
                )
            )

        # 2. Duplicates (for ID-like columns)
        if col.lower().endswith("_id") and len(non_null) > 0:
            dup_count = int(series.duplicated().sum())
            if dup_count > 0:
                dup_pct = dup_count / total_rows * 100
                issues.append(
                    QualityIssue(
                        id=_iid(),
                        dimension="uniqueness",
                        severity="high" if dup_pct > 5 else "medium",
                        column=col,
                        issue_type="duplicate_values",
                        description=f"{col}: {dup_count} duplicate values ({dup_pct:.1f}%)",
                        affected_rows=dup_count,
                        affected_pct=round(dup_pct, 2),
                        suggestion="Investigate duplicates — may indicate data quality issues",
                    )
                )

        # 3. Mixed data types
        if len(non_null) > 10:
            types = non_null.map(type).nunique()
            if types > 1:
                issues.append(
                    QualityIssue(
                        id=_iid(),
                        dimension="consistency",
                        severity="medium",
                        column=col,
                        issue_type="mixed_types",
                        description=f"{col}: contains {types} different data types",
                        affected_rows=total_rows - null_count,
                        suggestion="Standardize column data type",
                    )
                )

        # 4. Invalid emails
        if non_null.dtype == object and len(non_null) > 0:
            sample = non_null.head(200)
            if sample.str.contains(r"@").any():
                invalid_emails = int((~sample.astype(str).str.match(_EMAIL_RE, na=False)).sum())
                if invalid_emails > 0 and invalid_emails < len(sample) * 0.5:
                    issues.append(
                        QualityIssue(
                            id=_iid(),
                            dimension="validity",
                            severity="medium",
                            column=col,
                            issue_type="invalid_format",
                            description=f"{col}: {invalid_emails} values don't match email format",
                            affected_rows=invalid_emails,
                            suggestion="Validate and correct email addresses",
                        )
                    )

        # 5. Negative values in revenue/amount columns
        if col.lower() in ("revenue", "amount", "total", "price", "income", "sales"):
            numeric = pd.to_numeric(non_null, errors="coerce")
            neg_count = int((numeric < 0).sum())
            if neg_count > 0:
                issues.append(
                    QualityIssue(
                        id=_iid(),
                        dimension="accuracy",
                        severity="high",
                        column=col,
                        issue_type="negative_values",
                        description=f"{col}: {neg_count} negative values detected",
                        affected_rows=neg_count,
                        affected_pct=round(neg_count / total_rows * 100, 2),
                        suggestion="Verify if negative values are valid (returns/refunds) or errors",
                    )
                )

        # 6. Outliers (Z-score > 3)
        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            if len(numeric) > 20:
                mean = numeric.mean()
                std = numeric.std()
                if std > 0:
                    z_scores = np.abs((numeric - mean) / std)
                    outlier_count = int((z_scores > 3).sum())
                    if outlier_count > 0:
                        issues.append(
                            QualityIssue(
                                id=_iid(),
                                dimension="accuracy",
                                severity="low" if outlier_count < 10 else "medium",
                                column=col,
                                issue_type="outliers",
                                description=f"{col}: {outlier_count} statistical outliers (|z| > 3)",
                                affected_rows=outlier_count,
                                affected_pct=round(outlier_count / len(series) * 100, 2),
                                suggestion="Investigate outliers — may be errors or genuine extreme values",
                            )
                        )

        # 7. Inconsistent categories
        if series.dtype == object and non_null.nunique() > 5 and non_null.nunique() < 500:
            lower = non_null.str.lower().str.strip()
            if lower.nunique() < non_null.nunique():
                merge_count = int(non_null.nunique() - lower.nunique())
                issues.append(
                    QualityIssue(
                        id=_iid(),
                        dimension="consistency",
                        severity="low",
                        column=col,
                        issue_type="inconsistent_categories",
                        description=f"{col}: {merge_count} categories can be merged (case/whitespace inconsistencies)",
                        affected_rows=merge_count,
                        suggestion="Standardize text case and trim whitespace",
                    )
                )

    # ---- User-supplied rules ----
    if rules:
        for rule in rules:
            rule_type = rule.get("type", "")
            col_name = rule.get("column", "")

            if rule_type == "not_null" and col_name in df.columns:
                nc = int(df[col_name].isna().sum())
                if nc > 0:
                    issues.append(
                        QualityIssue(
                            id=_iid(),
                            dimension="validity",
                            severity=rule.get("severity", "medium"),
                            column=col_name,
                            issue_type="rule_not_null",
                            description=f"Rule: {col_name} must not be null — {nc} violations",
                            affected_rows=nc,
                            suggestion="Fill missing values",
                        )
                    )

            elif rule_type == "unique" and col_name in df.columns:
                dc = int(df[col_name].duplicated().sum())
                if dc > 0:
                    issues.append(
                        QualityIssue(
                            id=_iid(),
                            dimension="uniqueness",
                            severity=rule.get("severity", "medium"),
                            column=col_name,
                            issue_type="rule_unique",
                            description=f"Rule: {col_name} must be unique — {dc} duplicates",
                            affected_rows=dc,
                            suggestion="Remove duplicates",
                        )
                    )

            elif rule_type == "range" and col_name in df.columns:
                lo = rule.get("min")
                hi = rule.get("max")
                numeric = pd.to_numeric(df[col_name], errors="coerce")
                violations = 0
                if lo is not None:
                    violations += int((numeric < lo).sum())
                if hi is not None:
                    violations += int((numeric > hi).sum())
                if violations > 0:
                    issues.append(
                        QualityIssue(
                            id=_iid(),
                            dimension="accuracy",
                            severity=rule.get("severity", "medium"),
                            column=col_name,
                            issue_type="rule_range",
                            description=f"Rule: {col_name} must be in [{lo}, {hi}] — {violations} violations",
                            affected_rows=violations,
                            suggestion="Correct out-of-range values",
                        )
                    )

    # ---- Compute quality score ----
    len(issues)
    severity_weight = {"critical": 15, "high": 10, "medium": 5, "low": 2}
    total_deduction = sum(severity_weight.get(i.severity, 3) for i in issues)
    deduction = min(total_deduction, 80)

    # Per-dimension scores
    dim_counts: dict[str, int] = {}
    for i in issues:
        dim_counts[i.dimension] = dim_counts.get(i.dimension, 0) + 1

    def _dim_score(dim: str) -> float:
        c = dim_counts.get(dim, 0)
        return max(0, round(100 - c * 8, 1))

    score = QualityScore(
        overall=max(0, round(100 - deduction, 1)),
        completeness=_dim_score("completeness"),
        consistency=_dim_score("consistency"),
        accuracy=_dim_score("accuracy"),
        uniqueness=_dim_score("uniqueness"),
        validity=_dim_score("validity"),
        timeliness=_dim_score("timeliness"),
    )

    return issues, score
