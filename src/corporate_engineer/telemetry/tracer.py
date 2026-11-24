"""
OpenTelemetry-compatible Agent Tracer for AI Software Engineering (IMP-0009).
Tracks spans, parent-child hierarchies, latencies, tokens, and errors across agent DAGs.
"""

import contextvars
import secrets
import threading
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone  # type: ignore[assignment]

    UTC = timezone.utc  # type: ignore[assignment] # noqa: UP017

from corporate_engineer.models import AgentSpan, TraceReport


def generate_trace_id() -> str:
    """Generate a standard 32-hex character OpenTelemetry trace ID."""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generate a standard 16-hex character OpenTelemetry span ID."""
    return secrets.token_hex(8)


_ACTIVE_SPAN_STACK: contextvars.ContextVar[tuple[AgentSpan, ...]] = contextvars.ContextVar(
    "active_span_stack", default=()
)


class AgentTracer:
    """Thread-safe, async-safe and context-manager friendly OpenTelemetry span tracker."""

    def __init__(
        self, trace_id: str | None = None, service_name: str = "corporate-engineer"
    ) -> None:
        self.trace_id = trace_id or generate_trace_id()
        self.service_name = service_name
        self.spans: list[AgentSpan] = []
        self._lock: threading.RLock = threading.RLock()

    @property
    def _active_stack(self) -> list[AgentSpan]:
        return list(_ACTIVE_SPAN_STACK.get())

    @_active_stack.setter
    def _active_stack(self, val: list[AgentSpan]) -> None:
        _ACTIVE_SPAN_STACK.set(tuple(val))

    def start_span(
        self,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> AgentSpan:
        """Start a new span and append it to internal trace collection."""
        span_id = generate_span_id()
        now_iso = datetime.now(UTC).isoformat()

        with self._lock:
            parent_id = parent_span_id
            active = _ACTIVE_SPAN_STACK.get()
            if parent_id is None and active:
                parent_id = active[-1].span_id

            attrs: dict[str, Any] = {"service.name": self.service_name}
            if attributes:
                attrs.update(attributes)

            span = AgentSpan(
                trace_id=self.trace_id,
                span_id=span_id,
                parent_span_id=parent_id,
                name=name,
                start_time_iso=now_iso,
                attributes=attrs,
            )
            self.spans.append(span)
            return span

    def end_span(
        self,
        span: AgentSpan,
        status: str = "OK",
        error_message: str | None = None,
    ) -> None:
        """Complete a span, calculating duration and final status."""
        with self._lock:
            span.end_time_iso = datetime.now(UTC).isoformat()
            span.status = status
            span.error_message = error_message

            try:
                start_dt = datetime.fromisoformat(span.start_time_iso)
                end_dt = datetime.fromisoformat(span.end_time_iso)
                span.duration_ms = round((end_dt - start_dt).total_seconds() * 1000.0, 2)
            except (ValueError, TypeError, OSError):
                span.duration_ms = 0.0

    @contextmanager
    def span(
        self,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[AgentSpan, None, None]:
        """Context manager to scope a span with automatic duration and exception handling."""
        span_obj = self.start_span(name, parent_span_id=parent_span_id, attributes=attributes)
        token = _ACTIVE_SPAN_STACK.set(_ACTIVE_SPAN_STACK.get() + (span_obj,))
        start_mono = time.monotonic()
        try:
            yield span_obj
            self.end_span(span_obj, status="OK")
            # Refine duration with monotonic precision if possible
            elapsed_ms = round((time.monotonic() - start_mono) * 1000.0, 2)
            with self._lock:
                span_obj.duration_ms = max(span_obj.duration_ms, elapsed_ms)
        except Exception as e:
            elapsed_ms = round((time.monotonic() - start_mono) * 1000.0, 2)
            with self._lock:
                span_obj.duration_ms = elapsed_ms
            self.end_span(span_obj, status="ERROR", error_message=str(e))
            raise
        finally:
            _ACTIVE_SPAN_STACK.reset(token)

    def export_trace(self) -> TraceReport:
        """Export all recorded spans into an aggregated TraceReport."""
        with self._lock:
            spans_copy = list(self.spans)
            root_spans = [s for s in spans_copy if s.parent_span_id is None]
            root_name = root_spans[0].name if root_spans else "workflow.root"

            total_duration = (
                sum(s.duration_ms for s in root_spans)
                if root_spans
                else sum(s.duration_ms for s in spans_copy)
            )
            overall_status = "ERROR" if any(s.status == "ERROR" for s in spans_copy) else "OK"

            total_tokens = 0
            for s in spans_copy:
                attrs = s.attributes
                tot = attrs.get("gen_ai.usage.total_tokens")
                tok = attrs.get("tokens")
                prompt_tok = attrs.get("gen_ai.usage.prompt_tokens")
                comp_tok = attrs.get("gen_ai.usage.completion_tokens")

                if isinstance(tot, (int, float)):
                    total_tokens += int(tot)
                elif isinstance(tok, (int, float)):
                    total_tokens += int(tok)
                else:
                    sum_partial = 0
                    has_partial = False
                    if isinstance(prompt_tok, (int, float)):
                        sum_partial += int(prompt_tok)
                        has_partial = True
                    if isinstance(comp_tok, (int, float)):
                        sum_partial += int(comp_tok)
                        has_partial = True
                    if has_partial:
                        total_tokens += sum_partial

            return TraceReport(
                trace_id=self.trace_id,
                root_span_name=root_name,
                total_spans=len(spans_copy),
                total_duration_ms=round(total_duration, 2),
                total_tokens=total_tokens,
                spans=spans_copy,
                status=overall_status,
            )

    def export_json(self, output_path: str | Path | None = None) -> str:
        """Serialize trace report to JSON and optionally save to disk."""
        report = self.export_trace()
        json_output = report.model_dump_json(indent=2)
        if output_path:
            p = Path(output_path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json_output, encoding="utf-8")
        return json_output
