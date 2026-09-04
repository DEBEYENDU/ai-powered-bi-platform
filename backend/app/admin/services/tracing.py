"""Distributed tracing (correlation IDs + spans, stdlib only).

OpenTelemetry SDK is the production path; this module provides the same
shape (trace_id/span_id/parent, timed spans with attributes) without requiring
the dependency, and exporters can forward finished spans to OTel/Grafana.
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import Any

trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")
span_stack_ctx: ContextVar[tuple] = ContextVar("span_stack", default=())


class Tracer:
    def __init__(self, max_spans: int = 5000) -> None:
        self._spans: list[dict[str, Any]] = []
        self._max_spans = max_spans

    def start_trace(self, name: str, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = uuid.uuid4().hex
        trace_id_ctx.set(trace_id)
        span_stack_ctx.set(())
        return self.start_span(name, attributes)

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
        stack = span_stack_ctx.get()
        parent = stack[-1]["span_id"] if stack else None
        span = {
            "trace_id": trace_id_ctx.get() or uuid.uuid4().hex,
            "span_id": uuid.uuid4().hex[:16],
            "parent_span_id": parent,
            "name": name,
            "attributes": attributes or {},
            "start": time.time(),
            "end": None,
            "duration_ms": None,
        }
        trace_id_ctx.set(span["trace_id"])
        span_stack_ctx.set((*stack, span))
        return span

    def end_span(
        self, span: dict[str, Any], attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        span["end"] = time.time()
        span["duration_ms"] = round((span["end"] - span["start"]) * 1000, 3)
        if attributes:
            span["attributes"].update(attributes)
        stack = [s for s in span_stack_ctx.get() if s["span_id"] != span["span_id"]]
        span_stack_ctx.set(tuple(stack))
        self._spans.append(span)
        if len(self._spans) > self._max_spans:
            self._spans = self._spans[-self._max_spans :]
        return span

    def trace(self, name: str, attributes: dict[str, Any] | None = None):  # type: ignore[no-untyped-def]
        tracer = self

        class _Ctx:
            def __enter__(self) -> dict[str, Any]:
                self.span = tracer.start_span(name, attributes)
                return self.span

            def __exit__(self, *exc: Any) -> None:
                tracer.end_span(self.span)

        return _Ctx()

    def spans_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        return [s for s in self._spans if s["trace_id"] == trace_id]

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._spans[-limit:]
