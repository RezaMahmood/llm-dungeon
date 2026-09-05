"""FR-005 / contract §4: a request carrying a W3C `traceparent` header (as sent by the
frontend's Application Insights JS SDK on every outbound dependency call) must be
parented under that same trace on the backend side, so an engineer can reconstruct
"one user action, two systems" as a single Application Insights trace.
"""

from __future__ import annotations

import azure.functions as func

from backend.function_app import auth_me

INCOMING_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
INCOMING_TRACEPARENT = f"00-{INCOMING_TRACE_ID}-00f067aa0ba902b7-01"


def test_incoming_traceparent_parents_the_backend_span(otel_exporters):
    span_exporter, _log_exporter = otel_exporters
    req = func.HttpRequest(
        method="GET",
        url="/api/auth/me",
        headers={"traceparent": INCOMING_TRACEPARENT},
        params={},
        route_params={},
        body=b"",
    )

    auth_me(req)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert format(spans[0].context.trace_id, "032x") == INCOMING_TRACE_ID


def test_incoming_traceparent_correlates_regardless_of_header_casing(otel_exporters):
    """HTTP header names are case-insensitive; a proxy or client sending
    `Traceparent`/`TRACEPARENT` rather than the canonical lowercase form must
    not silently break correlation."""
    span_exporter, _log_exporter = otel_exporters
    req = func.HttpRequest(
        method="GET",
        url="/api/auth/me",
        headers={"TraceParent": INCOMING_TRACEPARENT},
        params={},
        route_params={},
        body=b"",
    )

    auth_me(req)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert format(spans[0].context.trace_id, "032x") == INCOMING_TRACE_ID
