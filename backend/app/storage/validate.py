"""Storage path validation utilities.

Provides defense-in-depth against path traversal attacks for all file
serving endpoints, even when the upstream code (e.g. DB records) is
trusted.

Usage::

    from app.storage.validate import validate_storage_path

    # In a download endpoint:
    validate_storage_path(path, allowed_root=settings.reports_path)
"""

from __future__ import annotations

import re
from pathlib import Path


class PathTraversalError(Exception):
    """Raised when a file path escapes its allowed root directory."""


def validate_storage_path(path: str | Path, allowed_root: str | Path) -> Path:
    """Resolve *path* and ensure it is contained within *allowed_root*.

    Checks performed:
    1. Normalisation via ``pathlib.Path.resolve()`` (follows symlinks).
    2. The resolved path must be a direct child of (or equal to) *allowed_root*.
    3. The resolved path must exist on disk.

    Raises
    ------
    PathTraversalError
        If the path escapes the allowed root.
    FileNotFoundError
        If the resolved path does not exist.

    Returns
    -------
    Path
        The resolved, validated ``Path`` object.
    """
    resolved = Path(path).resolve()
    root = Path(allowed_root).resolve()

    # Check containment: resolved must be root or a descendant of root.
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PathTraversalError(
            f"Path escapes allowed root: {path!r} is outside {root!r}"
        ) from exc

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")

    return resolved


def sanitize_user_filename(filename: str, max_length: int = 200) -> str:
    """Sanitize a user-supplied filename for safe storage.

    - Strips directory components (``../`` attacks).
    - Removes characters unsafe on Windows, Linux, and macOS.
    - Truncates to *max_length*.
    - Falls back to ``"upload"`` if the result is empty.
    """
    # Strip path separators
    name = Path(filename).name
    # Remove unsafe characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name).strip("_")
    # Truncate
    if len(name) > max_length:
        name = name[:max_length]
    return name or "upload"
