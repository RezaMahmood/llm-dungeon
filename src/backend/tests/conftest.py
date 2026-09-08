"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import logging

import azure.functions as func
import pytest
from opentelemetry import trace

from backend.models.story import CharacterType, CompletionCriteria, StartingPoint, Story
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


def _make_starting_point(**overrides) -> StartingPoint:
    """Builds a valid `StartingPoint` — the story's fixed opening scene (#271)."""
    defaults = dict(
        narrativeText="Fog rolls off the cove, and the lighthouse stands dark.",
        suggestedActions=["Walk to the lighthouse", "Search the shoreline"],
        locationLabel="Gullwing Cove path",
        goalLabel="Find the keeper",
    )
    defaults.update(overrides)
    return StartingPoint(**defaults)


@pytest.fixture
def _starting_point():
    return _make_starting_point


def _make_story(**overrides) -> Story:
    """Builds a valid `Story` for tests, with sensible defaults for every required field.
    Promoted from test_story_service.py's local `_story(**overrides)` helper so every test
    module builds a `Story` the same way (012-story-editing-and-review tasks.md T002)."""
    defaults = dict(
        id="story-1",
        worldPrompt="A half-abandoned lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
        narrativeGuidance="Keep it eerie but safe.",
        startingPoint=_make_starting_point(),
        createdBy="admin-oid",
        createdAt="2026-08-30T00:00:00Z",
        contentUpdatedAt="2026-08-30T00:00:00Z",
    )
    defaults.update(overrides)
    return Story(**defaults)


@pytest.fixture
def _story():
    return _make_story
