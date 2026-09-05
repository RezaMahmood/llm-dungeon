# Data Model: OpenTelemetry Observability Instrumentation

This feature adds no persisted application data (no database entities). Its "entities" are
telemetry shapes — spans, log records, and their attributes — as they will appear in
Application Insights. This document defines those shapes; `contracts/telemetry-schema.md`
gives the concrete field-by-field contract implementation and tests must satisfy.

## Trace / Span

A single request or operation's timing, status, and correlation identity.

| Field | Source | Notes |
|---|---|---|
| `trace_id` / `span_id` | OTel SDK (auto) | W3C trace-context; shared across frontend↔backend when correlated (FR-005) |
| `parent_span_id` | OTel SDK (auto) | Backend request span is a child of the frontend's dependency span when correlated |
| `name` | OTel semantic conventions (auto for HTTP spans) or explicit (`gen_ai.*` spans) | e.g. `POST /api/auth/login`, `gen_ai.story_creation.exchange` |
| `kind` | OTel SDK (auto) | `SERVER` (backend request), `CLIENT` (frontend dependency call), `INTERNAL` |
| `status` | OTel SDK (auto from HTTP status / exception) | `OK` / `ERROR`; FR-002 requires `ERROR` + exception event on every unhandled route exception |
| `start_time` / `duration` | OTel SDK (auto) | Backs SC-001's "outcome (status code, duration)" |
| `attributes.http.method`, `.route`, `.status_code` | OTel HTTP semantic conventions (auto) | Never includes header values (FR-006) |
| `attributes.enduser.id` | NOT set | No user PII in telemetry attributes (Principle X) — correlate by `trace_id`, not identity |

**Relationships**: A frontend page-interaction span (Application Insights JS SDK "PageView"
or dependency event) is the parent of the backend request span it triggered, connected via
W3C `traceparent` propagation (User Story 2, FR-005). An LLM call span (`gen_ai.*`,
`services/llm_service.py`) is a child of the backend request span that invoked it — this
relationship already exists in the codebase and is unchanged by this feature.

**Validation rules**: No span attribute may ever contain a bearer token, password, or other
credential value (FR-006) — enforced by never passing such a value into `span.set_attribute`
or an instrumentation library's captured header allow-list (research.md §6), not by scrubbing.

## Log Record

A structured, severity-leveled event emitted during a span.

| Field | Source | Notes |
|---|---|---|
| `severity` | Existing `logger.info/warning/error/exception(...)` calls | Unchanged call sites (FR-008) |
| `body` | Existing log message string | Preserved verbatim (spec Assumption: no content change) |
| `attributes` | Existing `extra={...}` kwargs at each call site | e.g. `login.py`'s `user_oid`, `roles` — already field-queryable once routed through OTel (FR-003) |
| `trace_id` / `span_id` | OTel logging auto-instrumentation | Correlates the log record to the request/operation that produced it (FR-003) |
| `exception.type`, `.message`, `.stacktrace` | OTel logging auto-instrumentation, from `logger.exception(...)`'s `exc_info` | Backs FR-002's "full stack trace, linked to the request" |

**Validation rules**: Same credential/PII exclusion rule as spans — no `extra` kwarg at any
existing or new call site may carry token/password values (spot-checked in research.md §6;
`data-model.md`'s role here is naming the rule so `tasks.md` can turn it into an explicit test
per touched call site, not re-auditing every call site here).

## Telemetry Attribute Schema (forward-looking, FR-007)

Not a new entity — this documents the existing, reusable attribute *pattern* a future LLM
call span should follow, taken directly from `services/llm_service.py`'s current spans (no
new fields invented by this feature):

| Attribute | Type | Meaning |
|---|---|---|
| `gen_ai.prompt` | string | Full prompt sent to the model |
| `gen_ai.response` | string | Full response received |
| `gen_ai.usage.input_tokens` | int | Input token count |
| `gen_ai.usage.output_tokens` | int | Output token count |
| `gen_ai.cost_usd` | float | Computed cost for the call |
| `gen_ai.latency_ms` | float | Call latency |

**Extensibility**: Additional `gen_ai.*` attributes (e.g. a future model-identifier or
session-attribution field) can be added to a span at any time — OTel spans have no fixed
schema to migrate, satisfying FR-007 without further design here.

## Frontend Telemetry Events (Application Insights JS SDK vocabulary)

| Event type | Trigger | Correlated to backend via |
|---|---|---|
| PageView | Route change (via `@microsoft/applicationinsights-react-js` plugin) | N/A (frontend-only event; the interaction it leads to correlates via its own dependency call) |
| Exception | Unhandled JS error / promise rejection, or a React render error caught by `observability/ErrorBoundary.jsx` | `trace_id` of the current operation, if any |
| Dependency (success) | Outbound `axios`/XHR call that receives a backend response | `traceparent` header shared with the backend's request span (FR-005) |
| Dependency (failure, no response) | Outbound call that fails before reaching the backend (network error, timeout) | Captured as its own event even with no backend counterpart to correlate to (FR-005a) — this is the one event type that is *expected* to sometimes have no matching backend span |
