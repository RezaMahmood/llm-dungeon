"""OpenTelemetry SDK bootstrap: the single path from backend code to Application
Insights (Principle VI, FR-001/FR-002/FR-003/FR-008).

`configure_azure_monitor()` (the Azure Monitor OpenTelemetry Distro) wires up
tracing, logging, and metrics export in one call. It does not auto-instrument
Azure Functions HTTP triggers — no such instrumentor ships in this distro's
supported library set, so `backend.function_app._guarded()` creates the
request SERVER span and performs the W3C `traceparent` extraction from
incoming headers itself. `configure_azure_monitor()` does auto-instrument the
Python stdlib `logging` module, though. Attaching its `LoggingHandler`
to the root logger (the default when `logger_name` is left unset) is what makes
every existing `logging.getLogger(...)` call site's records — regardless of
which named logger the site uses — flow through as trace/span-correlated OTel
log records with their `extra` kwargs preserved as individually queryable
attributes, with no call-site changes (FR-003, FR-008).
"""

from __future__ import annotations

import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor


def setup_observability() -> None:
    """Configure OpenTelemetry export to Application Insights, once, at startup.

    A no-op when `APPLICATIONINSIGHTS_CONNECTION_STRING` isn't set (e.g. local
    dev without the connection string configured) — `configure_azure_monitor()`
    raises rather than no-opping if it's absent, so this guard is required, not
    optional. Resilience when Application Insights itself is unreachable or the
    connection string is misconfigured is 018-observability-resilience's scope,
    not this one.
    """
    if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        # Python's root logger defaults to WARNING, which would silently drop
        # every existing `logger.info(...)` call site (e.g. login.py's "Login
        # succeeded") before it ever reaches the OTel LoggingHandler —
        # FR-003 names info/warning/error explicitly, so info must not be
        # filtered out here.
        logging.getLogger().setLevel(logging.INFO)
        configure_azure_monitor()
