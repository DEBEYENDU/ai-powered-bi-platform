"""Data loader — reads uploaded files and database connections into DataFrames,
with a local storage layer for uploaded files."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import get_settings


def _storage_root() -> Path:
    settings = get_settings()
    base = Path(getattr(settings, "storage_path", "/tmp/bi_storage"))
    root = base / "de_datasets"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _versions_root() -> Path:
    settings = get_settings()
    base = Path(getattr(settings, "storage_path", "/tmp/bi_storage"))
    root = base / "de_versions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def generate_dataset_id() -> str:
    return str(uuid.uuid4())


def load_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs)


def load_excel(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_excel(path, **kwargs)


def load_json(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_json(path, **kwargs)


def load_parquet(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_parquet(path, **kwargs)


def load_from_file(path: str | Path, source_type: str = "csv", **kwargs: Any) -> pd.DataFrame:
    """Dispatch to the appropriate loader based on source_type."""
    loaders = {
        "csv": load_csv,
        "excel": load_excel,
        "xlsx": load_excel,
        "json": load_json,
        "parquet": load_parquet,
    }
    loader = loaders.get(source_type.lower(), load_csv)
    return loader(path, **kwargs)


def load_from_upload(
    file_content: bytes,
    filename: str,
    source_type: str = "csv",
) -> tuple[pd.DataFrame, str, int]:
    """Persist uploaded file to storage and return (df, dataset_id, file_size)."""
    dataset_id = generate_dataset_id()
    root = _storage_root()
    dest = root / f"{dataset_id}_{filename}"
    dest.write_bytes(file_content)
    file_size = len(file_content)

    df = load_from_file(dest, source_type)
    return df, dataset_id, file_size


def save_dataframe(
    df: pd.DataFrame,
    dataset_id: str,
    suffix: str = "",
) -> str:
    """Persist a DataFrame as parquet and return the storage path."""
    root = _versions_root()
    fname = f"{dataset_id}{('_' + suffix) if suffix else ''}.parquet"
    dest = root / fname
    df.to_parquet(dest, index=False)
    return str(dest)


def load_stored_dataset(dataset_id: str, suffix: str = "") -> pd.DataFrame:
    """Load a previously stored DataFrame."""
    root = _versions_root()
    fname = f"{dataset_id}{('_' + suffix) if suffix else ''}.parquet"
    path = root / fname
    if not path.exists():
        # Try CSV fallback
        csv_path = root / f"{dataset_id}.csv"
        if csv_path.exists():
            return pd.read_csv(csv_path)
        raise FileNotFoundError(f"Dataset {dataset_id} not found")
    return pd.read_parquet(path)


def export_dataframe(
    df: pd.DataFrame,
    format: str = "csv",
) -> tuple[bytes, str, str]:
    """Export DataFrame as bytes. Returns (content, filename, mime_type)."""
    dataset_id = str(uuid.uuid4())[:8]

    if format == "csv":
        content = df.to_csv(index=False).encode("utf-8")
        return content, f"export_{dataset_id}.csv", "text/csv"
    elif format == "excel":
        buf = pd.ExcelWriter("/tmp/_export.xlsx", engine="openpyxl")
        df.to_excel(buf, index=False)
        buf.close()
        with open("/tmp/_export.xlsx", "rb") as f:
            content = f.read()
        os.remove("/tmp/_export.xlsx")
        return content, f"export_{dataset_id}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif format == "parquet":
        buf = "/tmp/_export.parquet"
        df.to_parquet(buf, index=False)
        with open(buf, "rb") as f:
            content = f.read()
        os.remove(buf)
        return content, f"export_{dataset_id}.parquet", "application/octet-stream"
    elif format == "json":
        content = df.to_json(orient="records", indent=2).encode("utf-8")
        return content, f"export_{dataset_id}.json", "application/json"
    elif format == "sql":
        # Generate INSERT statements
        table_name = "exported_data"
        cols = list(df.columns)
        inserts: list[str] = []
        for _, row in df.head(1000).iterrows():
            vals = ", ".join(_sql_literal(v) for v in row)
            inserts.append(f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({vals});")
        content = "\n".join(inserts).encode("utf-8")
        return content, f"export_{dataset_id}.sql", "text/plain"
    else:
        content = df.to_csv(index=False).encode("utf-8")
        return content, f"export_{dataset_id}.csv", "text/csv"


def _sql_literal(val: Any) -> str:
    if pd.isna(val):
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    return f"'{str(val).replace(chr(39), chr(39)+chr(39))}'"
