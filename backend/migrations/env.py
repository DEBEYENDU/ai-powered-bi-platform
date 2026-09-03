"""Alembic environment. Run from backend/: alembic upgrade head."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context  # type: ignore
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.db.base import Base

# Import models so metadata is complete.
import app.admin.models.admin  # noqa: F401
import app.dataset.models.dataset  # noqa: F401
import app.etl.models.job  # noqa: F401
import app.iam.models.user  # noqa: F401
import app.reports.models.report  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=get_settings().database_url,
                      target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_settings().database_url, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
