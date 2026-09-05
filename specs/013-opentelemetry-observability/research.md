# Research: OpenTelemetry Observability Instrumentation

## 1. Backend OTel bootstrap: what already exists vs. what's missing

**Decision**: Keep `configure_azure_monitor()` (Azure Monitor OpenTelemetry Distro) as the
single backend bootstrap call in `function_app.py`, called once at module import time before
any route is registered (already the case). Extend it rather than replace it: it already
auto-instruments the Python root `logging` module (so every `logger.info/warning/exception`
call site becomes an OTel log record automatically — no call-site rewrites needed) and
Azure Functions HTTP triggers (request spans with W3C context extraction from incoming
headers, satisfying half of FR-005/FR-005a's correlation requirement on the receiving side).

**Rationale**: `services/llm_service.py` (built in 006-adventure-and-character-setup) already
proves this bootstrap works in this codebase — its `gen_ai.*` spans are children of the
request span `configure_azure_monitor()` creates. Re-architecting the bootstrap (e.g. hand-
rolling OTel SDK setup instead of the Distro) would be pure risk with no requirement driving
it (Principle IV).

**What's actually missing** (the concrete gap the spec names — login 500s not showing up):
- `host.json` still configures the Azure Functions **host's own**, non-OTel Application
  Insights logging bridge (`logging.applicationInsights.samplingSettings`). This is a
  *separate* pipeline from `configure_azure_monitor()`'s in-process OTel SDK — it captures
  host-level function-invocation logs via the Functions runtime's own worker-to-host log
  channel, not via OTel. Running both means: (a) potential duplicate/inconsistent telemetry,
  and (b) FR-008's requirement ("routed through the OpenTelemetry logging pipeline rather than
  the... built-in, non-OpenTelemetry Application Insights bridge") is not actually met while
  this block stays as-is. **Action**: remove/neutralize the host-level bridge's log forwarding
  so OTel is the only path from backend code to Application Insights (the host still needs
  `host.json` for its own operational logging; only the Application Insights *forwarding* of
  it is what's being removed as a competing telemetry path).
- `_guarded()` in `function_app.py` already calls `logger.exception(...)` on every unhandled
  route exception, which — once OTel's logging instrumentation is confirmed to record
  exception info (`exc_info`) as a proper OTel exception log record, not just a formatted
  string — should satisfy FR-002. This needs a test (`tests/integration/`) forcing a route to
  raise, then asserting an OTel exception record with a stack trace was captured, not just
  "no crash" — this is exactly the gap the spec's `/api/auth/login` anecdote describes: the
  code *looks* like it should already work, but nothing currently proves it does end-to-end.
- `configure_azure_monitor()` is currently only called when
  `APPLICATIONINSIGHTS_CONNECTION_STRING` is set (skipped locally) — correct for this spec's
  scope (018-observability-resilience covers unconfigured/unreachable behavior), but means
  local dev has no telemetry today; tests must use OTel's in-memory span/log exporters
  directly rather than depending on `configure_azure_monitor()`'s live wiring.

**Alternatives considered**: Hand-rolled `TracerProvider`/`LoggerProvider` setup with the
plain `opentelemetry-sdk` + a manually configured Azure Monitor exporter — rejected; the
Distro (`azure-monitor-opentelemetry`) already does this correctly and is already a
dependency, so hand-rolling it would be unjustified complexity (Principle IV).

## 2. Backend structured logging → OTel log records (FR-003, FR-008)

**Decision**: Existing `logging.getLogger(...)` call sites across `api/**/*.py` and
`services/**/*.py` stay as-is in content and call shape (the spec explicitly says preserve
them); `configure_azure_monitor()`'s built-in `LoggingInstrumentor` attaches an OTel log
handler to the root logger, which is sufficient to turn every existing `logger.info(...,
extra={...})` call into a structured, request-correlated OTel log record — `extra` kwargs
already used in the codebase (e.g. `login.py`'s `extra={"user_oid": user_oid}`) map directly
to OTel log record attributes, so FR-003 ("queryable by field") is satisfied without a
call-site migration, only bootstrap configuration.

**Rationale**: This is the "migrates... rather than deleting or renaming" assumption stated
directly in spec.md's Assumptions section — the design goal is a transport change, not a
logging-API change.

**Alternatives considered**: A custom structured-logging wrapper (e.g. `structlog`) — rejected
as unnecessary; OTel's logging auto-instrumentation already captures Python's stdlib `extra`
fields as attributes, so adding a second logging abstraction would duplicate what
`configure_azure_monitor()` already provides.

## 3. Frontend telemetry client: OTel Web SDK vs. Application Insights JS SDK

**Decision**: `@microsoft/applicationinsights-web` + `@microsoft/applicationinsights-react-js`,
configured with `distributedTracingMode: DistributedTracingModes.W3C` (the modern default) and
CORS correlation enabled for the backend's origin(s), instead of a literal OpenTelemetry Web
SDK (`@opentelemetry/sdk-trace-web`).

**Rationale**: Confirmed via research (see Sources) that Azure ships **no supported
OpenTelemetry→Application Insights exporter for browser environments** —
`@azure/monitor-opentelemetry-exporter` is explicitly Node.js-only (its own docs say browser
users should use the Application Insights JavaScript SDK instead), and there is no first-party
browser alternative. A raw OTel Web SDK setup would therefore need either (a) an unsupported/
community OTLP exporter plus a self-hosted OpenTelemetry Collector to bridge into Application
Insights — new infrastructure with no stated requirement, conflicting with Principle XII — or
(b) simply not exporting anywhere, which fails FR-004 outright. The Application Insights JS
SDK is Microsoft's own supported browser client for this exact sink, and — critically for
FR-005/FR-005a — defaults to the same **W3C Trace-Context** standard (`traceparent` header)
that `configure_azure_monitor()`'s OTel HTTP instrumentation already reads on the backend, so
frontend and backend spans still merge into one correlated Application Insights trace even
though the frontend client is not literally an "OTel SDK". This is a deliberate, narrow,
user-approved exception to Principle VI's literal wording (Constitution Check in plan.md) —
the OTel *protocol* (W3C context propagation) is preserved end-to-end even though the
*library* on the browser leg isn't OTel-branded.

**Alternatives considered**:
1. Raw OTel Web SDK (`@opentelemetry/sdk-trace-web`, `instrumentation-fetch`,
   `instrumentation-xml-http-request`, `instrumentation-document-load`) + a self-hosted OTel
   Collector forwarding to Application Insights — rejected: new persistent infrastructure
   component with no stated requirement (Principle XII), and no Microsoft support path if it
   breaks.
2. Plain `console`/manual `fetch` calls to the Application Insights ingestion REST endpoint —
   rejected: reinvents batching, retry, sampling, and W3C header propagation that the
   Application Insights JS SDK already provides; far more code for the same outcome.
3. Do nothing on the frontend (backend-only telemetry) — rejected outright: this is
   User Story 2 in its entirety and FR-004/FR-005/FR-005a are explicit, non-negotiable
   requirements.

## 4. Frontend↔backend distributed-trace correlation (FR-005)

**Decision**: Enable the Application Insights JS SDK's automatic dependency tracking
(`AjaxPlugin`, on by default) with `enableCorsCorrelation: true` and the backend's origin(s)
included in `correlationHeaderDomains` (or left to match-all, since this app only calls its
own backend). This makes the SDK inject a `traceparent` (W3C) header on every outbound
`XMLHttpRequest`/`fetch` call — which covers `axios`, since axios uses the browser's
`XMLHttpRequest` adapter by default and the AjaxPlugin patches `XMLHttpRequest.prototype` — so
no change to `tokenInterceptor.js` or the `axios` service files is needed for correlation to
work; the header is injected transparently below the interceptor layer. On the receiving side,
`configure_azure_monitor()`'s existing OTel HTTP server instrumentation for Azure Functions
already extracts incoming W3C trace-context headers to parent the backend's request span
under the frontend's operation — this is standard OTel behavior requiring no extra backend
code, only verification via an integration test.

**Rationale**: Avoids touching the request/response interceptor pipeline (lower risk than
adding manual header injection there) and matches how both SDKs are designed to be used
together — this is the intended, documented interoperability point between the two Microsoft
telemetry stacks.

**Alternatives considered**: Manually reading `traceparent` from a context object and setting
it in `tokenInterceptor.js`'s request interceptor — rejected as redundant/riskier duplicate
logic once the AjaxPlugin already does this automatically; would also require the SDK context
to be threaded into the interceptor, adding coupling that isn't otherwise needed.

## 5. Frontend-only failures (FR-005a: request never reaches the backend)

**Decision**: Rely on the Application Insights JS SDK's automatic dependency-failure tracking
— when `AjaxPlugin` observes a network-level XHR/fetch failure (no response at all, e.g.
`onerror`/timeout before any HTTP status), it records a failed dependency telemetry event on
its own, independent of whether the backend ever received the request. No custom
try/catch-and-report wrapper around the existing `axios` service calls is needed; this is
the SDK's default behavior for exactly this case, and `tokenInterceptor.js`'s existing
`.catch`/rejection flow is left untouched (it still needs to reject the promise for the
calling UI code's own error handling — only telemetry capture is layered on top,
automatically, not replacing that flow).

**Rationale**: Directly satisfies FR-005a ("MUST always capture and report this as its own
telemetry event; not an unspecified/best-effort gap") using existing SDK behavior rather than
new application code, minimizing surface area for bugs in the very code path (network
failure) that's hardest to test reliably.

**Alternatives considered**: A custom axios response-interceptor `catch` clause that manually
calls `appInsights.trackException(...)` on network errors — rejected as redundant with what
the AjaxPlugin already does automatically, and riskier (a hand-written interceptor could
itself have a bug that silently drops the telemetry event FR-005a requires be unconditional).
Retained only as a documented fallback tests should also assert against if the automatic
dependency tracking is ever found not to fire on a genuinely offline `axios` call
(`tests/observability/` should include this exact scenario).

## 6. Credential/PII exclusion from telemetry (FR-006, Principle X)

**Decision**: No redaction/scrubbing layer. Rely on: (a) OTel's HTTP semantic-convention
instrumentation not capturing header *values* (including `Authorization`) by default — only
selected, explicitly allow-listed headers are ever captured, and none are configured here; (b)
existing backend `logger.*` call sites already avoid logging raw tokens/passwords (spot-
checked in `api/auth/login.py`, `api/auth/middleware.py` — they log `user_oid`/`email`/roles,
never the bearer token itself); (c) the Application Insights JS SDK's default dependency
tracking captures URL/method/status/duration, not request/response bodies or headers, so
tokens passed as `Authorization` header values are never captured on the frontend leg either.

**Rationale**: Matches the spec's stated Assumption directly: "achieved by never passing
credential material into any telemetry API to begin with, rather than by post-hoc redaction."
This also means SC-004 verification is a test that walks representative failure-path requests
and asserts no captured span/log attribute or event contains the raw token/password string
used in the test fixture — not a scan for a redaction marker.

**Alternatives considered**: An OTel `SpanProcessor`/log-record processor that scrubs known
sensitive attribute keys — rejected as unnecessary defense-in-depth for a codebase where no
call site currently passes credentials into a telemetry API; adding it without a concrete gap
driving it would be premature complexity (Principle IV). If a future audit finds a call site
that *does* leak credential material, the fix there is removing that call site's offending
argument, not adding a global scrubber.

## 7. LLM-call telemetry forward-compatibility (FR-007)

**Decision**: No new schema work. `services/llm_service.py`'s existing `gen_ai.*` span
attributes (`gen_ai.prompt`, `gen_ai.response`, `gen_ai.usage.input_tokens`,
`gen_ai.usage.output_tokens`, `gen_ai.cost_usd`, `gen_ai.latency_ms`) already demonstrate the
attribute-based extensibility FR-007 requires — attaching more attributes to a span is
non-breaking by construction in OTel (no schema migration exists to "break"). This spec's only
action item here is documenting the existing pattern in `contracts/telemetry-schema.md` as the
convention future LLM call sites (008-core-gameplay) should follow, satisfying "accounted for
in the design" without inventing anything new.

**Rationale**: Directly matches spec.md's Assumptions: "does not define the final ...schema in
detail — it only ensures the chosen instrumentation approach ... is the right shape to extend
later." That shape already exists in the codebase from 006-adventure-and-character-setup.

**Alternatives considered**: Defining a formal, versioned attribute schema document ahead of
any second LLM call site — rejected as speculative; one real example (the story-creation
exchange/generation calls) is enough precedent, and OTel attributes need no upfront schema
versioning to extend safely later.

---

### Sources

- [@azure/monitor-opentelemetry-exporter (npm)](https://www.npmjs.com/package/@azure/monitor-opentelemetry-exporter) — confirms Node.js-only support, browser users directed to the Application Insights JS SDK.
- [Enable OpenTelemetry in Application Insights — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable)
- [Application Insights OpenTelemetry observability overview — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
