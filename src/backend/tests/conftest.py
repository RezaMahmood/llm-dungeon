"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import logging

import azure.functions as func
import pytest
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Module-level (not per-test) because OTel's global TracerProvider/LoggerProvider
# can only be set once per process — `trace.set_tracer_provider()` silently no-ops
# on a second call. Tests get isolation instead via the `otel_exporters` fixture
# below, which clears these exporters' captured spans/log records between tests.
_span_exporter = InMemorySpanExporter()
_tracer_provider = TracerProvider()
_tracer_provider.add_span_processor(SimpleSpanProcessor(_span_exporter))
trace.set_tracer_provider(_tracer_provider)

_log_exporter = InMemoryLogRecordExporter()
_logger_provider = LoggerProvider()
_logger_provider.add_log_record_processor(SimpleLogRecordProcessor(_log_exporter))
set_logger_provider(_logger_provider)
# Attaches to the root logger (matches configure_azure_monitor()'s default
# `logger_name=""` in production), so every existing `logging.getLogger(...)`
# call site is captured without per-site changes (FR-003, FR-008).
LoggingInstrumentor().instrument(logger_provider=_logger_provider, set_logging_format=False)
# Matches observability/setup.py's production configuration — the root logger's
# default WARNING level would otherwise silently drop every `logger.info(...)`
# call site before it reaches the OTel LoggingHandler (FR-003).
logging.getLogger().setLevel(logging.INFO)


@pytest.fixture
def otel_exporters():
    """In-memory span/log exporters, reset before each test that uses them."""
    _span_exporter.clear()
    _log_exporter.clear()
    yield _span_exporter, _log_exporter


def make_request(
    method: str = "GET",
    url: str = "/api/test",
    token: str | None = None,
    body: bytes = b"",
    route_params: dict | None = None,
) -> func.HttpRequest:
    headers = {}
    if token is not None:
        headers["X-Custom-Authorization"] = f"Bearer {token}"
    return func.HttpRequest(method=method, url=url, headers=headers, params={}, route_params=route_params or {}, body=body)


@pytest.fixture
def request_factory():
    return make_request
