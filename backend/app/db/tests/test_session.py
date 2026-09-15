"""Tests for database session configuration."""

from __future__ import annotations


class TestDatabasePool:
    """Verify the SQLAlchemy engine is created with correct pool settings."""

    def test_engine_pool_settings(self) -> None:
        """Engine should have pool_size, max_overflow, pool_timeout, pool_recycle."""
        # Reset so get_engine() creates a fresh engine
        import app.db.session as _mod
        from app.db.session import get_engine

        _engine_backup = _mod._engine
        _mod._engine = None
        try:
            engine = get_engine()
            pool = engine.pool
            assert pool.size() == 10, f"Expected pool_size=10, got {pool.size()}"
            assert pool._max_overflow == 20, f"Expected max_overflow=20, got {pool._max_overflow}"
            assert pool._timeout == 10, f"Expected pool_timeout=10, got {pool._timeout}"
            assert pool._recycle == 1800, f"Expected pool_recycle=1800, got {pool._recycle}"
        finally:
            _mod._engine = _engine_backup

    def test_engine_uses_pre_ping(self) -> None:
        import app.db.session as _mod
        from app.db.session import get_engine

        _engine_backup = _mod._engine
        _mod._engine = None
        try:
            engine = get_engine()
            assert engine.pool._pre_ping is True
        finally:
            _mod._engine = _engine_backup
