# Telemetry Contract: OpenTelemetry → Application Insights

This is the "interface" this feature exposes: not an HTTP API, but the telemetry shape other
code (future LLM call sites, future dashboards/workbooks, an on-call engineer's Application
Insights queries) can depend on. Implementation tests (`tasks.md`) must assert against this
contract directly, not just "telemetry was emitted somehow."

## 1. Backend request/exception contract (FR-001, FR-002, User Story 1)

For every backend HTTP route registered in `function_app.py`:

- **On success**: exactly one `SERVER`-kind span exists with `http.route` matching the
  registered route, `http.status_code` matching the response, and a duration. Any
  `logger.info/warning(...)` call made while handling the request produces a log record whose
  `trace_id`/`span_id` match this span's.
- **On an unhandled exception** (anything `_guarded()` catches): the request span's `status`
  is `ERROR`, the span carries an exception event with `exception.type`, `exception.message`,
  and `exception.stacktrace` populated (not empty/truncated), and a corresponding OTel log
  record exists (from `logger.exception(...)`) whose `trace_id`/`span_id` match the same span.
  **Zero exceptions may reach the client as a generic 500 with no matching span/log record** —
  this is SC-002's 100% bar, and the concrete regression test for the `/api/auth/login`
  anecdote in spec.md's rationale.
- **Never present**: any span or log-record attribute equal to, or containing as a substring,
  a raw `Authorization` header value, bearer token, or password from the triggering request
  (FR-006). Tests should assert this directly against a known test-fixture credential value,
  not merely "no attribute named `token`".

## 2. Backend log-record field contract (FR-003, FR-008)

- Every existing `logger.<level>(message, extra={...})` call site's `extra` keys appear as
  named, individually queryable attributes on the resulting OTel log record — not concatenated
  into the free-text `body`.
- No telemetry from backend code reaches Application Insights via any path other than the OTel
  SDK (`configure_azure_monitor()`) — specifically, `host.json`'s host-level Application
  Insights log forwarding must not be a second, parallel path once this feature is complete
  (research.md §1).

## 3. Frontend telemetry contract (FR-004, User Story 2)

- **PageView**: emitted on every route change, carrying at minimum the route/page name.
- **Exception**: emitted for (a) any unhandled `window.onerror`/`onunhandledrejection` event,
  and (b) any error caught by `observability/ErrorBoundary.jsx`, each carrying a message and
  stack trace.
- **Dependency — reached backend**: emitted for every outbound `axios`/XHR call that receives
  any HTTP response (success or error status), carrying URL, method, status, and duration —
  never request/response body or header values.
- **Dependency — never reached backend (FR-005a)**: emitted for every outbound call that fails
  before any response is received (network failure, timeout, DNS failure, offline). This event
  MUST exist even though no corresponding backend span exists to correlate it to — its absence
  is the failure mode FR-005a exists to prevent.

## 4. Frontend↔backend correlation contract (FR-005)

- Every Dependency event that *did* reach the backend carries a `traceparent`-derived
  `trace_id` that is identical to the `trace_id` of the backend request span it triggered.
  This is the field an engineer queries on to reconstruct "one user action, two systems" as a
  single Application Insights trace (SC-003) — the test for this is an integration test that
  triggers a real frontend→backend call (e.g. login) and asserts both sides' captured
  `trace_id` match, not merely "both sides emitted something."

## 5. LLM-call telemetry contract (FR-007, forward-looking only)

- Any future LLM call span MUST be a child of the request span that triggered it (already true
  of `services/llm_service.py`'s `gen_ai.*` spans) and MUST use the `gen_ai.*` attribute names
  listed in `data-model.md`'s Telemetry Attribute Schema section for prompt, response, token
  counts, cost, and latency, so aggregate Application Insights queries can rely on consistent
  field names across every LLM call site, present and future. No call site is added by this
  feature — this contract line exists so 008-core-gameplay's implementer (human or AI) has a
  contract to follow rather than inventing new field names per call site.
