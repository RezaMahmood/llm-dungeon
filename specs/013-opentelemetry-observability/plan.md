# Implementation Plan: OpenTelemetry Observability Instrumentation

**Branch**: `013-opentelemetry-observability` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-opentelemetry-observability/spec.md`

## Summary

Make Azure Application Insights a trustworthy, queryable record of backend and frontend
behavior by routing all telemetry through OpenTelemetry. On the backend (Python Azure
Functions), this means: finish wiring `configure_azure_monitor()` so every unhandled
exception, request outcome, and existing `logging` call site is exported as structured,
request-correlated OTel telemetry — replacing the Functions host's own, non-OTel
Application Insights bridge (`host.json`'s `logging.applicationInsights` block) rather than
running both in parallel. On the frontend (ReactJS), add Microsoft's Application Insights
JavaScript SDK — the only Microsoft-supported browser client for this sink, since Azure ships
no supported OpenTelemetry browser exporter — configured for W3C distributed-tracing mode so
frontend spans (page views, unhandled JS exceptions, outbound API calls, including calls that
never reach the backend) correlate into the same Application Insights trace as the OTel spans
the backend already emits. No LLM call sites are added by this feature (008-core-gameplay
does that), but `services/llm_service.py` already emits `gen_ai.*` OTel spans (built during
006-adventure-and-character-setup) whose attribute shape is treated as the working
precedent/schema for any future LLM span, satisfying FR-007 without new design work here.

## Technical Context

**Language/Version**: Python 3.11 (Azure Functions, `src/backend`) + JavaScript (ES2022) /
JSX, React 18.3, Node.js LTS tooling via Vite 8 (`src/frontend`)

**Primary Dependencies**:
- Backend (already present in `requirements.txt`): `azure-monitor-opentelemetry` (Azure
  Monitor OpenTelemetry Distro — bundles `opentelemetry-sdk`, the Azure Functions/requests/
  logging auto-instrumentors, and the Azure Monitor exporter), `opentelemetry-api` (already
  used directly in `services/llm_service.py` for `gen_ai.*` spans).
- Frontend (new): `@microsoft/applicationinsights-web` (browser telemetry client, W3C
  distributed-tracing mode) and `@microsoft/applicationinsights-react-js` (React error
  boundary / route-change page-view plugin, avoids hand-rolling React Router page-view
  tracking).

**Storage**: N/A — this feature adds no persisted application data; Application Insights /
Log Analytics (already provisioned by 007-azure-infrastructure-provisioning) is the telemetry
store, out of scope to reprovision here.

**Testing**: pytest (`src/backend/tests`, already the backend convention) for span/log-record
emission and PII/credential-exclusion assertions using the OTel SDK's in-memory span/log
exporters; Vitest + Testing Library (`src/frontend/tests`, already the frontend convention)
for frontend telemetry initialization, exception capture, and outbound-call correlation
header assertions, mocking `@microsoft/applicationinsights-web`'s channel.

**Target Platform**: Backend — Azure Functions (Linux, Flex Consumption, Python 3.11) per
007-azure-infrastructure-provisioning; Frontend — evergreen browsers via the existing static
web app hosting.

**Project Type**: Web application (existing `src/backend` + `src/frontend` split)

**Performance Goals**: No new performance goals (Principle IV) — telemetry emission must not
be the reason a request or page interaction becomes perceptibly slower; the OTel SDK's default
batching/async export behavior (already relied on for `gen_ai.*` spans) is sufficient and no
custom tuning is in scope.

**Constraints**:
- FR-006 / Principle X: telemetry must never carry bearer tokens, passwords, or other PII —
  enforced by never passing that data into a telemetry API (spec's stated approach), not by
  post-hoc scrubbing.
- Principle VI (NON-NEGOTIABLE): OTel is the collector layer end-to-end; Application Insights
  is the only sink. The frontend's Application Insights JS SDK is a documented, user-approved
  exception to literal "OTel SDK" wording for the browser leg only, justified because Azure
  provides no supported OTel→Application Insights browser exporter (see research.md §5 and
  Constitution Check below) — the backend leg remains literal OTel SDK end-to-end.
- This spec assumes Application Insights is reachable and correctly configured; resilience
  when it is not is out of scope (018-observability-resilience).

**Scale/Scope**: Instruments the existing ~15 backend HTTP routes (`function_app.py`) and the
existing frontend page/route set and `axios`-based API services (`gameService.js`,
`authService.js`, `accountService.js`, `storyDraftService.js`); no new user-facing screens or
endpoints.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle VI (Observability & AI Cost Transparency, NON-NEGOTIABLE)** — Backend: OTel
  SDK end-to-end (already the pattern for `gen_ai.*` spans; this feature extends it to
  request/exception/log telemetry and removes the competing host-level bridge). Frontend:
  **explicit, user-approved deviation** — Application Insights JS SDK stands in for a literal
  OTel Web SDK because no supported Azure Monitor browser OTel exporter exists (research.md
  §5); it uses the same W3C Trace-Context propagation OTel uses, so User Story 2's
  frontend↔backend correlation requirement is still met technically, even though the frontend
  client itself is not an OTel SDK. Confirmed with the requesting user during planning (this
  session) rather than assumed. LLM-call telemetry shape (prompt, response, tokens, cost,
  latency) is unchanged from the existing `gen_ai.*` spans in `llm_service.py` — FR-007 is
  satisfied by precedent, no new schema invented. **PASS (with documented, approved
  exception)**.
- **Principle X / PII & Data Protection** — FR-006 requires never passing credential material
  into a telemetry API. `Authorization` headers, tokens, and passwords are excluded from OTel
  HTTP instrumentation's captured attributes by default (the OTel HTTP semantic conventions do
  not capture header values unless explicitly configured to), and this plan does not add any
  configuration that would capture them; `data-model.md` and `contracts/` make the excluded
  fields explicit so implementation/tests can verify it directly. **PASS**.
- **Principle II / Secure-by-Default Access** — No new endpoints, no anonymous routes added;
  telemetry wiring runs inside the existing authenticated request lifecycle. **PASS**.
- **Principle XII / Right-Sized Scope** — No new Azure resource, environment, or service is
  provisioned; this feature only changes how the application talks to the Application Insights
  sink 007-azure-infrastructure-provisioning already stood up. Rejected the raw-OTel-Web-SDK +
  self-hosted OTel Collector alternative specifically because it would require standing up new
  infrastructure with no stated requirement for it. **PASS**.
- **Principle VIII / UI Design System** — This feature adds no user-facing UI (no new screens,
  no visual changes); the UI Design System Requirements section does not apply. **N/A**.
- **Principle XI / UI Design Pre-Agreement** — No user-facing UI is added, so no design
  mockup/sign-off task is required in `tasks.md`. **N/A**.
- **Principle I / Meaningful, Automated Testing** — Backend and frontend telemetry emission is
  independently testable in-process via OTel's in-memory exporters (backend) and a mocked
  Application Insights channel (frontend), with no live Azure dependency required — consistent
  with the "no dedicated test cloud environment" constraint. **PASS**.

No violations requiring `## Complexity Tracking` remain after the frontend-SDK decision above
was confirmed with the user.

## Project Structure

### Documentation (this feature)

```text
specs/013-opentelemetry-observability/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── telemetry-schema.md
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/backend/
├── function_app.py           # Existing configure_azure_monitor() call-site; guarded-handler
│                              # wrapper (_guarded) is where exception recording gets finished
├── observability/            # NEW — small shared module, not a new "project"
│   ├── __init__.py
│   └── setup.py               # OTel SDK bootstrap: configure_azure_monitor() wiring,
│                               # logging-handler attachment, span/log correlation helpers
├── api/**/*.py                # Existing route handlers — structured `logger.*` calls already
│                               # exist here (FR-003/FR-008 migrate their transport, not content)
├── services/llm_service.py    # Existing gen_ai.* OTel spans — precedent for FR-007, unchanged
└── tests/
    ├── unit/                  # NEW: observability/ unit tests (span/log-record assertions)
    └── integration/           # NEW: end-to-end "unhandled exception -> exception telemetry"
                                # test per route, using OTel in-memory exporters

src/frontend/
├── src/
│   ├── observability/         # NEW — small shared module
│   │   ├── appInsights.js      # Application Insights JS SDK init, W3C correlation config
│   │   └── ErrorBoundary.jsx   # NEW — unhandled React render-error capture (App Insights
│   │                            # React plugin doesn't catch these on its own)
│   ├── services/               # Existing axios-based API services — instrumented via the
│   │                            # AI SDK's automatic XHR/fetch dependency tracking, no
│   │                            # per-call code change needed (tokenInterceptor.js untouched)
│   └── index.jsx                # Existing entry point — App Insights SDK initialized here,
│                                 # before React renders
└── tests/
    └── observability/          # NEW: init, exception-capture, and correlation-header tests
```

**Structure Decision**: Existing `src/backend` + `src/frontend` split is unchanged. This
feature adds one small `observability/` module per side (not a new top-level project) — a
shared place for OTel/App-Insights bootstrap code that both `function_app.py` and
`src/frontend/src/index.jsx` call into, keeping route handlers and page components themselves
free of telemetry-plumbing boilerplate.

## Complexity Tracking

*No entries — see Constitution Check above; the one deviation (frontend SDK choice) was
resolved by explicit user confirmation during planning, not left as an unjustified violation.*
