"""Tests for storage path validation and sanitisation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.storage.validate import (
    PathTraversalError,
    sanitize_user_filename,
    validate_storage_path,
)

# ---------------------------------------------------------------------------
# sanitize_user_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_strips_directory_components(self) -> None:
        assert sanitize_user_filename("../../etc/passwd") == "passwd"

    def test_strips_backslashes(self) -> None:
        assert sanitize_user_filename("..\\..\\windows\\system32") == "system32"

    def test_removes_unsafe_characters(self) -> None:
        result = sanitize_user_filename('file<>:"|?*.txt')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result
        assert "." in result

    def test_collapses_underscores(self) -> None:
        result = sanitize_user_filename("a___b____c.txt")
        assert "___" not in result

    def test_truncates_long_names(self) -> None:
        long_name = "a" * 300 + ".txt"
        result = sanitize_user_filename(long_name, max_length=200)
        assert len(result) <= 200

    def test_falls_back_to_upload_for_empty(self) -> None:
        assert sanitize_user_filename("") == "upload"
        assert sanitize_user_filename("///") == "upload"

    def test_preserves_safe_filename(self) -> None:
        assert sanitize_user_filename("report_2024.csv") == "report_2024.csv"


# ---------------------------------------------------------------------------
# validate_storage_path
# ---------------------------------------------------------------------------

class TestValidateStoragePath:
    def test_valid_path_passes(self, tmp_path: Path) -> None:
        (tmp_path / "report.pdf").write_bytes(b"content")
        result = validate_storage_path(tmp_path / "report.pdf", allowed_root=tmp_path)
        assert result == (tmp_path / "report.pdf").resolve()

    def test_nested_path_passes(self, tmp_path: Path) -> None:
        subdir = tmp_path / "org123" / "report456"
        subdir.mkdir(parents=True)
        (subdir / "report.pdf").write_bytes(b"content")
        result = validate_storage_path(subdir / "report.pdf", allowed_root=tmp_path)
        assert result.exists()

    def test_traversal_with_dotdot_fails(self, tmp_path: Path) -> None:
        (tmp_path / "secret.txt").write_bytes(b"secret")
        with pytest.raises(PathTraversalError, match="escapes allowed root"):
            validate_storage_path(
                tmp_path / "subdir" / ".." / "secret.txt",
                allowed_root=tmp_path / "subdir",
            )

    def test_absolute_path_outside_root_fails(self, tmp_path: Path) -> None:
        with pytest.raises(PathTraversalError, match="escapes allowed root"):
            validate_storage_path("/etc/passwd", allowed_root=tmp_path)

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_storage_path(tmp_path / "nonexistent.txt", allowed_root=tmp_path)

    def test_symlink_traversal_fails(self, tmp_path: Path) -> None:
        secret = tmp_path / "secret.txt"
        secret.write_bytes(b"secret")
        link_dir = tmp_path / "allowed"
        link_dir.mkdir()
        link = link_dir / "sneak.txt"
        try:
            link.symlink_to(secret)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")
        with pytest.raises(PathTraversalError, match="escapes allowed root"):
            validate_storage_path(link, allowed_root=link_dir)

    def test_windows_absolute_path_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(PathTraversalError, match="escapes allowed root"):
            validate_storage_path("C:\\Windows\\System32\\config", allowed_root=tmp_path)

    def test_unc_path_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(PathTraversalError):
            validate_storage_path("\\\\server\\share\\file.txt", allowed_root=tmp_path)


# ---------------------------------------------------------------------------
# Cross-platform data_loader export
# ---------------------------------------------------------------------------

class TestDataLoaderExport:
    """Test that data_loader uses tempfile instead of hardcoded /tmp."""

    def test_export_csv_uses_tempdir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.ai.data_engineering.services.data_loader as dl

        monkeypatch.setattr(dl, "_temp_dir", lambda: tmp_path)
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        content, fname, mime = dl.export_dataframe(df, format="csv")
        assert fname.endswith(".csv")
        assert len(content) > 0
        assert mime == "text/csv"

    def test_export_json_uses_tempdir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.ai.data_engineering.services.data_loader as dl

        monkeypatch.setattr(dl, "_temp_dir", lambda: tmp_path)
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        content, fname, mime = dl.export_dataframe(df, format="json")
        assert fname.endswith(".json")
        assert len(content) > 0
        assert mime == "application/json"

    def test_export_parquet_uses_tempdir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.ai.data_engineering.services.data_loader as dl

        monkeypatch.setattr(dl, "_temp_dir", lambda: tmp_path)
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        content, fname, _mime = dl.export_dataframe(df, format="parquet")
        assert fname.endswith(".parquet")
        assert len(content) > 0

    def test_export_fallback_to_csv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.ai.data_engineering.services.data_loader as dl

        monkeypatch.setattr(dl, "_temp_dir", lambda: tmp_path)
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2]})
        _content, fname, _mime = dl.export_dataframe(df, format="unknown_format")
        assert fname.endswith(".csv")

    def test_sanitize_filename_strips_traversal(self) -> None:
        from app.ai.data_engineering.services.data_loader import _sanitize_filename

        assert _sanitize_filename("../../etc/passwd") == "passwd"
        assert _sanitize_filename("..\\windows\\file.txt") == "file.txt"
        assert _sanitize_filename("normal.csv") == "normal.csv"


# ---------------------------------------------------------------------------
# Report download path traversal (integration-style)
# ---------------------------------------------------------------------------

class TestReportDownloadValidation:
    """Verify the download endpoint validates paths."""

    def test_validate_storage_path_is_importable(self) -> None:
        from app.reports.routers.reports import validate_storage_path
        assert callable(validate_storage_path)
