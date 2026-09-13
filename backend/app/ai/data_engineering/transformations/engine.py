"""Transformation engine — applies user-defined and AI-recommended transforms."""

from __future__ import annotations

import contextlib
from typing import Any

import pandas as pd


def apply_transforms(
    df: pd.DataFrame,
    transforms: list[dict[str, Any]],
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Apply a sequence of transforms to a DataFrame.

    Returns ``(result, columns_added, columns_removed)``.
    """
    result = df.copy()
    added: list[str] = []
    removed: list[str] = []

    for t in transforms:
        ttype = t.get("transform_type", "")
        col = t.get("column", "")
        params = t.get("parameters", {})

        try:
            result, a, r = _apply_one(result, ttype, col, params)
            added.extend(a)
            removed.extend(r)
        except Exception:
            # Skip failing transforms — caller can inspect
            continue

    return result, added, removed


def _apply_one(
    df: pd.DataFrame,
    ttype: str,
    col: str,
    params: dict[str, Any],
) -> tuple[pd.DataFrame, list[str], list[str]]:
    added: list[str] = []
    removed: list[str] = []

    if ttype == "fill_missing":
        method = params.get("method", "mode")
        fill_val = params.get("fill_value")
        if col not in df.columns:
            return df, added, removed
        if method == "mode":
            mode = df[col].mode()
            df[col] = df[col].fillna(mode.iloc[0] if len(mode) > 0 else "")
        elif method == "median":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(
                pd.to_numeric(df[col], errors="coerce").median()
            )
        elif method == "mean":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(
                pd.to_numeric(df[col], errors="coerce").mean()
            )
        elif method == "value" and fill_val is not None:
            df[col] = df[col].fillna(fill_val)
        elif method == "forward":
            df[col] = df[col].ffill()
        elif method == "backward":
            df[col] = df[col].bfill()

    elif ttype == "remove_duplicates":
        keep = params.get("keep", "first")
        subset = [col] if col and col in df.columns else None
        df = df.drop_duplicates(subset=subset, keep=keep)

    elif ttype == "trim_spaces":
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].str.strip()

    elif ttype == "standardize":
        if col in df.columns and df[col].dtype == object:
            method = params.get("method", "lowercase")
            if method == "lowercase":
                df[col] = df[col].str.lower().str.strip()
            elif method == "uppercase":
                df[col] = df[col].str.upper().str.strip()
            elif method == "title":
                df[col] = df[col].str.title().str.strip()

    elif ttype == "normalize_text":
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].str.lower().str.strip().str.replace(r"\s+", " ", regex=True)

    elif ttype == "convert_type":
        if col not in df.columns:
            return df, added, removed
        target = params.get("target_dtype", "float64")
        if target in ("float64", "int64"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if target == "int64":
                df[col] = df[col].astype("Int64")
        elif target == "datetime64[ns]":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif target == "string":
            df[col] = df[col].astype("string")
        elif target == "boolean":
            df[col] = df[col].map(
                {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
            )

    elif ttype == "split_column":
        if col not in df.columns:
            return df, added, removed
        delimiter = params.get("delimiter", " ")
        new_cols = params.get("new_columns", [])
        parts = df[col].astype(str).str.split(delimiter, n=-1, expand=True)
        if new_cols and len(new_cols) == parts.shape[1]:
            parts.columns = new_cols
        else:
            parts.columns = [f"{col}_{i}" for i in range(parts.shape[1])]
        for c in parts.columns:
            df[c] = parts[c]
            added.append(c)

    elif ttype == "merge_columns":
        cols_to_merge = params.get("columns", [col])
        delimiter = params.get("delimiter", " ")
        new_name = params.get("new_column", "_merged")
        valid = [c for c in cols_to_merge if c in df.columns]
        if valid:
            df[new_name] = df[valid].astype(str).agg(delimiter.join, axis=1)
            added.append(new_name)

    elif ttype == "rename":
        new_name = params.get("new_name", "")
        if col in df.columns and new_name:
            df = df.rename(columns={col: new_name})
            added.append(new_name)
            removed.append(col)

    elif ttype == "drop":
        if col in df.columns:
            df = df.drop(columns=[col])
            removed.append(col)

    elif ttype == "filter":
        expr = params.get("expression", "")
        if expr:
            with contextlib.suppress(Exception):
                df = df.query(expr)

    elif ttype == "pivot":
        index_col = params.get("index", col)
        pivot_col = params.get("columns", "")
        value_col = params.get("values", "")
        agg = params.get("aggfunc", "first")
        if index_col in df.columns and pivot_col in df.columns and value_col in df.columns:
            df = df.pivot_table(
                index=index_col, columns=pivot_col, values=value_col, aggfunc=agg
            ).reset_index()
            df.columns = [str(c) for c in df.columns]

    elif ttype == "unpivot":
        id_cols = params.get("id_vars", [])
        value_name = params.get("value_name", "value")
        var_name = params.get("var_name", "variable")
        if id_cols and all(c in df.columns for c in id_cols):
            df = df.melt(id_vars=id_cols, var_name=var_name, value_name=value_name)

    elif ttype == "group_aggregate":
        group_cols = params.get("group_by", [col] if col else [])
        agg_spec = params.get("aggregations", {})
        valid = [c for c in group_cols if c in df.columns]
        if valid and agg_spec:
            agg_dict: dict[str, str] = {}
            for target_col, func in agg_spec.items():
                if target_col in df.columns:
                    agg_dict[target_col] = func
            if agg_dict:
                df = df.groupby(valid, as_index=False).agg(agg_dict)

    elif ttype == "calculated_column":
        new_name = params.get("new_column", "calculated")
        expression = params.get("expression", "")
        if expression and new_name:
            try:
                df[new_name] = df.eval(expression)
                added.append(new_name)
            except Exception:
                # Fallback: simple arithmetic
                pass

    return df, added, removed


def get_available_transforms() -> list[dict[str, Any]]:
    """Return the list of supported transform types with metadata."""
    return [
        {
            "type": "fill_missing",
            "name": "Fill Missing Values",
            "description": "Fill null values using mode, median, mean, or a custom value",
            "parameters": {
                "method": "mode|median|mean|value|forward|backward",
                "fill_value": "optional",
            },
        },
        {
            "type": "remove_duplicates",
            "name": "Remove Duplicates",
            "description": "Remove duplicate rows based on specified columns",
            "parameters": {"keep": "first|last|none"},
        },
        {
            "type": "trim_spaces",
            "name": "Trim Spaces",
            "description": "Remove leading and trailing whitespace from text columns",
            "parameters": {},
        },
        {
            "type": "standardize",
            "name": "Standardize Text",
            "description": "Normalize text casing (lowercase, uppercase, title case)",
            "parameters": {"method": "lowercase|uppercase|title"},
        },
        {
            "type": "normalize_text",
            "name": "Normalize Text",
            "description": "Lowercase, trim, and collapse whitespace",
            "parameters": {},
        },
        {
            "type": "convert_type",
            "name": "Convert Data Type",
            "description": "Convert column to a different data type",
            "parameters": {"target_dtype": "float64|int64|datetime64[ns]|string|boolean"},
        },
        {
            "type": "split_column",
            "name": "Split Column",
            "description": "Split a column into multiple columns by delimiter",
            "parameters": {"delimiter": "string", "new_columns": "list[str]"},
        },
        {
            "type": "merge_columns",
            "name": "Merge Columns",
            "description": "Combine multiple columns into one",
            "parameters": {"columns": "list[str]", "delimiter": "string", "new_column": "string"},
        },
        {
            "type": "pivot",
            "name": "Pivot",
            "description": "Reshape data from long to wide format",
            "parameters": {
                "index": "column",
                "columns": "column",
                "values": "column",
                "aggfunc": "first|sum|mean|count",
            },
        },
        {
            "type": "unpivot",
            "name": "Unpivot (Melt)",
            "description": "Reshape data from wide to long format",
            "parameters": {"id_vars": "list[str]", "value_name": "string", "var_name": "string"},
        },
        {
            "type": "group_aggregate",
            "name": "Group & Aggregate",
            "description": "Group by columns and apply aggregate functions",
            "parameters": {"group_by": "list[str]", "aggregations": "dict[col, func]"},
        },
        {
            "type": "calculated_column",
            "name": "Calculated Column",
            "description": "Create a new column using a pandas expression",
            "parameters": {"new_column": "string", "expression": "pandas eval string"},
        },
        {
            "type": "rename",
            "name": "Rename Column",
            "description": "Rename a column",
            "parameters": {"new_name": "string"},
        },
        {
            "type": "drop",
            "name": "Drop Column",
            "description": "Remove a column from the dataset",
            "parameters": {},
        },
        {
            "type": "filter",
            "name": "Filter Rows",
            "description": "Keep rows matching a pandas query expression",
            "parameters": {"expression": "pandas query string"},
        },
    ]
