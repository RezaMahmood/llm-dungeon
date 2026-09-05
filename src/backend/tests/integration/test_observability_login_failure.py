"""Regression test for the spec's motivating gap: an unhandled exception in
/api/auth/login must not become a generic 500 with nothing queryable in
Application Insights (FR-002, SC-002, contract §1).
"""

from __future__ import annotations

from unittest.mock import patch

from backend.function_app import auth_login


def test_login_unhandled_exception_produces_linked_exception_span_and_log(otel_exporters, request_factory):
    span_exporter, log_exporter = otel_exporters
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")

    with patch("backend.api.auth.login.authenticate_with_email", side_effect=RuntimeError("cosmos unavailable")):
        response = auth_login(req)

    assert response.status_code == 500

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.status.status_code.name == "ERROR"
    exception_events = [event for event in span.events if event.name == "exception"]
    assert len(exception_events) == 1
    assert exception_events[0].attributes["exception.type"] == "RuntimeError"
    assert exception_events[0].attributes["exception.message"] == "cosmos unavailable"

    exception_logs = [
        record.log_record
        for record in log_exporter.get_finished_logs()
        if "Unhandled error" in record.log_record.body
    ]
    assert len(exception_logs) == 1
    log_record = exception_logs[0]
    assert log_record.trace_id == span.context.trace_id
    assert log_record.span_id == span.context.span_id
