"""FR-001 / FR-003 / contract §1-§2: a successful request produces a SERVER span with
http.route/http.status_code/duration, and a `logger.info(..., extra={...})` call made
during handling produces a log record correlated to that span, with `extra` keys
preserved as individually queryable attributes (not concatenated into free text).
"""

from __future__ import annotations

import logging

import azure.functions as func

from backend.function_app import _guarded

logger = logging.getLogger("tests.observability_success")


def _successful_handler(_req: func.HttpRequest) -> func.HttpResponse:
    logger.info("handled request", extra={"user_oid": "test-oid-123"})
    return func.HttpResponse(status_code=200)


def test_guarded_success_span_and_correlated_log_record(otel_exporters, request_factory):
    span_exporter, log_exporter = otel_exporters

    response = _guarded(_successful_handler)(request_factory(method="GET", url="/api/test"))

    assert response.status_code == 200

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.kind.name == "SERVER"
    assert span.attributes["http.route"] == "/api/test"
    assert span.attributes["http.status_code"] == 200
    assert span.status.status_code.name != "ERROR"
    assert span.end_time > span.start_time

    log_records = [
        record.log_record
        for record in log_exporter.get_finished_logs()
        if record.log_record.body == "handled request"
    ]
    assert len(log_records) == 1
    log_record = log_records[0]
    assert log_record.trace_id == span.context.trace_id
    assert log_record.span_id == span.context.span_id
    assert log_record.attributes["user_oid"] == "test-oid-123"


def test_guarded_normalizes_route_params_into_a_low_cardinality_template(otel_exporters, request_factory):
    """http.route must stay a route template (e.g. /manage/stories/{storyId}),
    not one unique string per concrete resource ID — otherwise it's
    high-cardinality and no longer queryable/aggregatable the way OTel's HTTP
    semantic conventions expect."""
    span_exporter, _log_exporter = otel_exporters

    req = request_factory(
        method="GET",
        url="/api/manage/stories/abc123",
        route_params={"storyId": "abc123"},
    )
    _guarded(_successful_handler)(req)

    span = span_exporter.get_finished_spans()[0]
    assert span.attributes["http.route"] == "/api/manage/stories/{storyId}"
