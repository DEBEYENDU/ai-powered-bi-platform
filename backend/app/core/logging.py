"""Structured logging.

Uses structlog (JSON) when installed; otherwise configures stdlib logging with
a request-id-aware formatter. ``get_logger`` is the single entry point.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_HAS_STRUCTLOG = False
try:
    import structlog  # type: ignore # noqa: F401 -- availability probe; used via lazy import in functions below

    _HAS_STRUCTLOG = True
except ImportError:
    pass


def configure_logging(level: str = "INFO") -> None:
    if _HAS_STRUCTLOG:
        import structlog  # type: ignore

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, level.upper(), logging.INFO)
            ),
        )
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","msg":"%(message)s"}'
            )
        )
        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> Any:
    if _HAS_STRUCTLOG:
        import structlog  # type: ignore

        return structlog.get_logger(name)
    return logging.getLogger(name)
