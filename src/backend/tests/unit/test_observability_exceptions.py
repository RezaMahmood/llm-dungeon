"""FR-002 / contract §1: every unhandled route exception becomes exception telemetry —
a span with status=ERROR and a populated exception event, never a silent generic 500
with no corresponding telemetry.
"""

from __future__ import annotations

import azure.functions as func

from backend.function_app import _guarded


def _raising_handler(_req: func.HttpRequest) -> func.HttpResponse:
    raise ValueError("boom")


def test_guarded_records_exception_and_error_status(otel_exporters, request_factory):
    span_exporter, _log_exporter = otel_exporters

    response = _guarded(_raising_handler)(request_factory(method="POST", url="/api/test"))

    assert response.status_code == 500

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.status.status_code.name == "ERROR"

    exception_events = [event for event in span.events if event.name == "exception"]
    assert len(exception_events) == 1
    attrs = exception_events[0].attributes
    assert attrs["exception.type"] == "ValueError"
    assert attrs["exception.message"] == "boom"
    assert attrs["exception.stacktrace"]
