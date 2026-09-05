# Quickstart: Validating OpenTelemetry Observability Instrumentation

This guide validates the two user stories independently, without needing a live Application
Insights instance for most checks — the OTel SDK's in-memory exporters (backend) and a mocked
Application Insights channel (frontend) are sufficient for automated validation; the final
steps validate against the real, deployed Application Insights instance per Principle IX.

## Prerequisites

- Backend: `src/backend` virtualenv with `requirements.txt` + `requirements-dev.txt` installed.
- Frontend: `src/frontend` with `npm install` run (after `tasks.md` adds
  `@microsoft/applicationinsights-web` + `@microsoft/applicationinsights-react-js` to
  `package.json`).
- No live Azure resources required for the automated checks below. The final acceptance step
  requires the deployed live environment (Principle IX) and read access to its Application
  Insights instance (007-azure-infrastructure-provisioning).

## User Story 1 — Backend request/exception telemetry (P1)

1. **Automated (local)**: Run the backend test suite —
   ```bash
   cd src/backend && python -m pytest tests/unit tests/integration -k observability
   ```
   Expected: a test that forces a route handler to raise asserts (a) an OTel span exists with
   `status=ERROR` and a populated exception event (type/message/stacktrace — see
   `contracts/telemetry-schema.md` §1), and (b) a log record from `_guarded()`'s
   `logger.exception(...)` call shares that span's `trace_id`. A second test asserts a
   successful request produces a span with the response's `status_code` and duration, plus any
   `logger.info(...)` calls made during handling as correlated log records with their `extra`
   kwargs present as individual attributes (contract §2).
2. **Automated (credential exclusion)**: A test sends a request with a known fixture bearer
   token and password-like value through both a success and a failure path, then asserts no
   captured span/log attribute contains that literal value (SC-004, contract §1).
3. **Manual, against the live environment (Principle IX final acceptance)**: Trigger a real
   backend error (e.g. an intentionally malformed `/api/auth/login` request in the deployed
   environment) and confirm in Application Insights → Failures that the exception, full stack
   trace, and originating request are visible and linked, within a few minutes of ingestion
   latency (SC-001).

## User Story 2 — Frontend↔backend correlated tracing (P2)

1. **Automated (local)**: Run the frontend test suite —
   ```bash
   cd src/frontend && npm test -- observability
   ```
   Expected: tests asserting (a) the Application Insights SDK is initialized once at app
   startup with W3C distributed-tracing mode enabled, (b) an unhandled error thrown inside the
   React tree is caught by `observability/ErrorBoundary.jsx` and reported as an Exception event
   with message + stack trace, and (c) a mocked outbound `axios` call that fails before any
   response (network error) still produces a Dependency-failure telemetry event (FR-005a,
   contract §3) — this is the specific "backend never saw it" scenario and must be tested
   explicitly, not inferred from the success-path test.
2. **Manual, against the live environment (Principle IX final acceptance)**: In the deployed
   app, sign in (a real frontend action that calls the backend). In Application Insights →
   Transaction search (or the End-to-end transaction view for that operation), confirm the
   frontend page interaction / dependency call and the backend's `/api/auth/login` request
   share one `trace_id` (SC-003) — not two unrelated entries. Then disconnect network access
   briefly and trigger a frontend API call to confirm it still appears as its own Application
   Insights event even with zero backend counterpart (FR-005a).

## Cross-cutting check

- Confirm `host.json`'s host-level Application Insights log-forwarding path no longer produces
  telemetry once the OTel path is live (research.md §1) — e.g. by diffing Application
  Insights' ingested telemetry before/after this feature's deploy for duplicate entries per
  request, or by inspecting the updated `host.json` directly for the removed/neutralized
  `logging.applicationInsights` forwarding.
  - **Result (T023)**: Confirmed locally — `src/host.json`'s `logging.applicationInsights`
    block (the host-level Application Insights forwarding path) has been removed, leaving only
    `logging.logLevel` for the host's own operational logging. `configure_azure_monitor()`
    (via `backend/observability/setup.py`) is now the only path from backend code to
    Application Insights.
- **FR-007 forward-compatibility (T023a)**: Confirmed `src/backend/services/llm_service.py`'s
  existing `gen_ai.*` span attributes (`gen_ai.prompt`, `gen_ai.response`,
  `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.cost_usd`,
  `gen_ai.latency_ms`) still match `data-model.md`'s Telemetry Attribute Schema / contract §5
  exactly — no new schema work was needed; this is the precedent 008-core-gameplay's future
  LLM call sites should follow.
