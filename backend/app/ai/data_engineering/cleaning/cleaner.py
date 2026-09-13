"""Automated data cleaning — suggest and apply cleaning operations."""

from __future__ import annotations

import uuid
from typing import Any

import pandas as pd

from app.ai.data_engineering.schemas import CleaningSuggestion


def _sid() -> str:
    return str(uuid.uuid4())[:8]


def suggest_cleaning(
    df: pd.DataFrame, profile: list[dict[str, Any]] | None = None
) -> list[CleaningSuggestion]:
    """Analyse a DataFrame and produce actionable cleaning suggestions."""
    suggestions: list[CleaningSuggestion] = []

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        null_count = int(series.isna().sum())
        total = len(series)

        # --- Missing values ---
        if null_count > 0:
            null_pct = null_count / total * 100
            if null_pct < 5:
                mode_val = series.mode()
                fill_val = str(mode_val.iloc[0]) if len(mode_val) > 0 else ""
                suggestions.append(
                    CleaningSuggestion(
                        id=_sid(),
                        column=col,
                        transform_type="fill_missing",
                        description=f"{col}: {null_count} nulls ({null_pct:.1f}%) — fill with mode '{fill_val}'",
                        current_state=f"{null_count} nulls",
                        proposed_state=f"Fill with '{fill_val}'",
                        affected_rows=null_count,
                        confidence=round(0.85 - null_pct * 0.01, 2),
                        auto_applicable=True,
                        parameters={"method": "mode", "fill_value": fill_val},
                    )
                )
            elif null_pct < 30:
                suggestions.append(
                    CleaningSuggestion(
                        id=_sid(),
                        column=col,
                        transform_type="fill_missing",
                        description=f"{col}: {null_count} nulls ({null_pct:.1f}%) — fill with median/mean",
                        current_state=f"{null_count} nulls",
                        proposed_state="Fill with statistical estimate",
                        affected_rows=null_count,
                        confidence=round(0.75 - null_pct * 0.005, 2),
                        auto_applicable=False,
                        parameters={"method": "median"},
                    )
                )
            else:
                suggestions.append(
                    CleaningSuggestion(
                        id=_sid(),
                        column=col,
                        transform_type="fill_missing",
                        description=f"{col}: {null_count} nulls ({null_pct:.1f}%) — consider dropping column or advanced imputation",
                        current_state=f"{null_count} nulls ({null_pct:.1f}%)",
                        proposed_state="Drop column or use advanced imputation",
                        affected_rows=null_count,
                        confidence=0.5,
                        auto_applicable=False,
                        parameters={"method": "flag"},
                    )
                )

        # --- Duplicates ---
        dup_count = int(series.duplicated().sum())
        if dup_count > 0 and col.lower().endswith("_id"):
            suggestions.append(
                CleaningSuggestion(
                    id=_sid(),
                    column=col,
                    transform_type="remove_duplicates",
                    description=f"{col}: {dup_count} duplicate IDs detected",
                    current_state=f"{dup_count} duplicates",
                    proposed_state="Remove duplicate rows",
                    affected_rows=dup_count,
                    confidence=0.9,
                    auto_applicable=False,
                    parameters={"keep": "first"},
                )
            )

        # --- Text standardization ---
        if series.dtype == object and len(non_null) > 0:
            trimmed = non_null.str.strip()
            untrimmed_count = int((trimmed != non_null).sum())
            if untrimmed_count > 0:
                suggestions.append(
                    CleaningSuggestion(
                        id=_sid(),
                        column=col,
                        transform_type="trim_spaces",
                        description=f"{col}: {untrimmed_count} values have leading/trailing spaces",
                        current_state=f"{untrimmed_count} untrimmed values",
                        proposed_state="Trimmed strings",
                        affected_rows=untrimmed_count,
                        confidence=0.95,
                        auto_applicable=True,
                        parameters={},
                    )
                )

            # Check for inconsistent casing
            lower_vals = non_null.str.lower()
            unique_lower = lower_vals.nunique()
            unique_original = non_null.nunique()
            if unique_lower < unique_original and unique_original > 1:
                suggestions.append(
                    CleaningSuggestion(
                        id=_sid(),
                        column=col,
                        transform_type="standardize",
                        description=f"{col}: inconsistent casing detected ({unique_original} → {unique_lower} unique values)",
                        current_state=f"{unique_original} unique values",
                        proposed_state=f"Standardized to {unique_lower} values",
                        affected_rows=int(unique_original - unique_lower),
                        confidence=0.85,
                        auto_applicable=True,
                        parameters={"method": "lowercase"},
                    )
                )

        # --- Type conversion ---
        if series.dtype == object and len(non_null) > 0:
            numeric_count = pd.to_numeric(non_null, errors="coerce").notna().sum()
            if numeric_count / len(non_null) > 0.9:
                suggestions.append(
                    CleaningSuggestion(
                        id=_sid(),
                        column=col,
                        transform_type="convert_type",
                        description=f"{col}: appears numeric — convert from text to number",
                        current_state="text/object",
                        proposed_state="numeric",
                        affected_rows=len(non_null),
                        confidence=round(numeric_count / len(non_null), 2),
                        auto_applicable=False,
                        parameters={"target_dtype": "float64"},
                    )
                )

            # Date conversion
            try:
                dates = pd.to_datetime(non_null.head(50), infer_datetime_format=True)
                if dates.notna().sum() / min(50, len(non_null)) > 0.8:
                    suggestions.append(
                        CleaningSuggestion(
                            id=_sid(),
                            column=col,
                            transform_type="convert_type",
                            description=f"{col}: appears to be a date column — convert to datetime",
                            current_state="text/object",
                            proposed_state="datetime64[ns]",
                            affected_rows=len(non_null),
                            confidence=0.85,
                            auto_applicable=False,
                            parameters={"target_dtype": "datetime64[ns]"},
                        )
                    )
            except (ValueError, TypeError):
                pass

    return suggestions


def apply_cleaning(
    df: pd.DataFrame, suggestions: list[CleaningSuggestion]
) -> tuple[pd.DataFrame, int]:
    """Apply selected cleaning suggestions. Returns (cleaned_df, cells_modified)."""
    cleaned = df.copy()
    cells_modified = 0

    for sug in suggestions:
        if sug.transform_type == "fill_missing":
            method = sug.parameters.get("method", "mode")
            fill_val = sug.parameters.get("fill_value", "")
            if method == "mode" and fill_val:
                cleaned[sug.column] = cleaned[sug.column].fillna(fill_val)
                cells_modified += int(cleaned[sug.column].isna().sum() == 0)
            elif method == "median":
                median_val = pd.to_numeric(cleaned[sug.column], errors="coerce").median()
                cleaned[sug.column] = cleaned[sug.column].fillna(median_val)
            elif method == "mean":
                mean_val = pd.to_numeric(cleaned[sug.column], errors="coerce").mean()
                cleaned[sug.column] = cleaned[sug.column].fillna(mean_val)

        elif sug.transform_type == "trim_spaces":
            if cleaned[sug.column].dtype == object:
                cleaned[sug.column] = cleaned[sug.column].str.strip()

        elif sug.transform_type == "standardize":
            method = sug.parameters.get("method", "lowercase")
            if method == "lowercase" and cleaned[sug.column].dtype == object:
                cleaned[sug.column] = cleaned[sug.column].str.lower().str.strip()

        elif sug.transform_type == "convert_type":
            target = sug.parameters.get("target_dtype", "float64")
            if target == "float64":
                cleaned[sug.column] = pd.to_numeric(cleaned[sug.column], errors="coerce")
            elif target == "datetime64[ns]":
                cleaned[sug.column] = pd.to_datetime(cleaned[sug.column], errors="coerce")

        elif sug.transform_type == "remove_duplicates":
            before = len(cleaned)
            cleaned = cleaned.drop_duplicates(subset=[sug.column], keep="first")
            cells_modified += before - len(cleaned)

    return cleaned, cells_modified
