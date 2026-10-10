"""Data loader — reads uploaded files and database connections into DataFrames,
with a local storage layer for uploaded files."""

from __future__ import annotations

import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import get_settings

# Characters that are unsafe in filenames across platforms.
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _sanitize_filename(name: str) -> str:
    """Remove path separators and unsafe characters from uploaded filenames."""
    # Strip directory components (attackers may send "../../etc/passwd")
    name = Path(name).name
    # Remove unsafe characters
    name = _UNSAFE_CHARS.sub("_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name).strip("_")
    # Enforce a reasonable length
    if len(name) > 200:
        name = name[:200]
    return name or "upload"


def _storage_root() -> Path:
    settings = get_settings()
    base = Path(getattr(settings, "storage_path", str(Path.cwd() / "storage")))
    root = base / "de_datasets"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _versions_root() -> Path:
    settings = get_settings()
    base = Path(getattr(settings, "storage_path", str(Path.cwd() / "storage")))
    root = base / "de_versions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _temp_dir() -> Path:
    """Cross-platform temporary directory for exports."""
    return Path(tempfile.mkdtemp(prefix="bi_export_"))


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
        "txt": load_csv,
        "excel": load_excel,
        "xlsx": load_excel,
        "json": load_json,
        "parquet": load_parquet,
    }
    loader = loaders.get(source_type.lower(), load_csv)
    return loader(path, **kwargs)


SUPPORTED_SOURCE_TYPES = {"csv", "txt", "excel", "xlsx", "json", "parquet"}


def validate_source_type(source_type: str) -> str:
    """Reject unknown file types instead of silently parsing them as CSV."""
    t = (source_type or "csv").lower()
    if t not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(
            f"Unsupported file type '{source_type}'. Supported types: csv, xlsx, json, parquet"
        )
    return t


def _check_size(file_content: bytes) -> None:
    """Enforce the configured dataset upload size limit before touching disk."""
    limit = int(getattr(get_settings(), "data_max_upload_size", 50 * 1024 * 1024))
    if len(file_content) > limit:
        raise ValueError(
            f"File size ({len(file_content) / (1024 * 1024):.1f} MB) exceeds the "
            f"{limit // (1024 * 1024)} MB dataset upload limit"
        )


def _reject_binary(file_content: bytes, source_type: str) -> None:
    """Refuse binary payloads for text formats before pandas sees them.

    ``pandas.read_csv`` happily accepts binary junk as a one-column table, so
    without this check a broken upload is reported as a successful dataset.
    """
    if source_type.lower() not in {"csv", "json", "txt"}:
        return
    if not file_content.strip():
        raise ValueError("Uploaded file is empty")
    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        text = file_content.decode("latin-1")
    control = [ch for ch in text if ord(ch) < 32 and ch not in "\t\r\n"]
    if control:
        raise ValueError("File contains binary data and is not a readable table")


def load_from_upload(
    file_content: bytes,
    filename: str,
    source_type: str = "csv",
) -> tuple[pd.DataFrame, str, int]:
    """Persist uploaded file to storage and return (df, dataset_id, file_size)."""
    validate_source_type(source_type)
    _check_size(file_content)
    _reject_binary(file_content, source_type)
    dataset_id = generate_dataset_id()
    safe_name = _sanitize_filename(filename)
    root = _storage_root()
    dest = root / f"{dataset_id}_{safe_name}"
    dest.write_bytes(file_content)
    file_size = len(file_content)

    try:
        df = load_from_file(dest, source_type)
    except Exception:
        # Never leave a rejected upload behind on disk.
        dest.unlink(missing_ok=True)
        raise
    if df.empty:
        dest.unlink(missing_ok=True)
        raise ValueError("The uploaded file contains no data rows")
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


def store_upload(
    dataset_id: str,
    file_content: bytes,
    filename: str,
    source_type: str = "csv",
) -> tuple[pd.DataFrame, int]:
    """Persist an uploaded file under an existing dataset id and parse it.

    Used by flows where the dataset record is created before the file arrives
    (``POST /api/v1/datasets/{id}/upload``).
    """
    validate_source_type(source_type)
    _check_size(file_content)
    _reject_binary(file_content, source_type)
    safe_name = _sanitize_filename(filename)
    dest = _storage_root() / f"{dataset_id}_{safe_name}"
    dest.write_bytes(file_content)
    try:
        df = load_from_file(dest, source_type)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    if df.empty:
        dest.unlink(missing_ok=True)
        raise ValueError("The uploaded file contains no data rows")
    return df, len(file_content)


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
    tmp = _temp_dir()

    if format == "csv":
        content = df.to_csv(index=False).encode("utf-8")
        return content, f"export_{dataset_id}.csv", "text/csv"
    elif format == "excel":
        xlsx_path = tmp / "export.xlsx"
        with pd.ExcelWriter(str(xlsx_path), engine="openpyxl") as buf:
            df.to_excel(buf, index=False)
        content = xlsx_path.read_bytes()
        xlsx_path.unlink(missing_ok=True)
        tmp.rmdir()
        return (
            content,
            f"export_{dataset_id}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    elif format == "parquet":
        pq_path = tmp / "export.parquet"
        df.to_parquet(str(pq_path), index=False)
        content = pq_path.read_bytes()
        pq_path.unlink(missing_ok=True)
        tmp.rmdir()
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
    return f"'{str(val).replace(chr(39), chr(39) + chr(39))}'"
