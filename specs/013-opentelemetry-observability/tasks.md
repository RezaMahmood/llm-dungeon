---

description: "Task list for OpenTelemetry Observability Instrumentation"
---

# Tasks: OpenTelemetry Observability Instrumentation

**Input**: Design documents from `/specs/013-opentelemetry-observability/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/telemetry-schema.md, quickstart.md

**Tests**: Included — `quickstart.md` specifies concrete pytest/vitest commands and assertions
(`-k observability`, `npm test -- observability`) that this feature's acceptance depends on, so
test tasks are in scope, not optional here.

**Organization**: Tasks are grouped by user story (US1 = backend telemetry, P1; US2 = frontend↔
backend correlation, P2) to enable independent implementation and testing of each.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Paths are repo-root-relative (`src/backend/...`, `src/frontend/...`)

## Path Conventions

Existing web app split: `src/backend/` (Python Azure Functions) + `src/frontend/` (React/Vite).

---

## Phase 1: Setup

**Purpose**: Add the one new frontend dependency this feature needs; backend dependencies
(`azure-monitor-opentelemetry`, `opentelemetry-api`) are already in `requirements.txt`.

- [X] T001 [P] Add `@microsoft/applicationinsights-web` and `@microsoft/applicationinsights-react-js` to `dependencies` in `src/frontend/package.json`
- [X] T002 Run `npm install` in `src/frontend` to resolve the new dependencies and update `package-lock.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend OTel bootstrap must be correct and be the *only* path to Application
Insights before either user story's tests can pass — US1 depends on it directly, and US2's
correlation tests depend on the backend already emitting correct spans to correlate against.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create `src/backend/observability/__init__.py` and `src/backend/observability/setup.py`: move the existing `configure_azure_monitor()` bootstrap (currently inline in `src/backend/function_app.py`) into a `setup_observability()` function here, preserving the existing `APPLICATIONINSIGHTS_CONNECTION_STRING`-present guard, and add explicit log-record correlation configuration so every `logging.getLogger(...)` call site's `trace_id`/`span_id` are attached (FR-003)
- [X] T004 Update `src/backend/function_app.py` to import and call `setup_observability()` from `backend.observability.setup` in place of the inline `configure_azure_monitor()` call
- [X] T005 Remove the host-level Application Insights log-forwarding path in `src/host.json` (neutralize the `logging.applicationInsights` block per research.md §1) so OTel (`configure_azure_monitor()`) is the only telemetry path to Application Insights, satisfying FR-008

**Checkpoint**: Foundation ready — backend emits OTel spans/logs via a single pipeline; user story implementation can now begin.

---

## Phase 3: User Story 1 - An Engineer Can Diagnose a Failed Backend Request from Application Insights Alone (Priority: P1) 🎯 MVP

**Goal**: Every backend request, unhandled exception, and existing log call site is exported as
structured, request-correlated OTel telemetry, with zero exceptions silently becoming a
telemetry-less generic 500.

**Independent Test**: Force a backend endpoint to raise an unhandled exception; verify (via
OTel in-memory exporters in tests, and manually in Application Insights) that the exception,
its stack trace, and the originating request are visible and linked.

### Tests for User Story 1

- [X] T006 [P] [US1] Unit test in `src/backend/tests/unit/test_observability_exceptions.py`: using the OTel SDK's in-memory span exporter, assert a route handler that raises produces a span with `status=ERROR` and an exception event with populated `exception.type`/`exception.message`/`exception.stacktrace` (contract §1)
- [X] T007 [P] [US1] Unit test in `src/backend/tests/unit/test_observability_success.py`: using in-memory span + log exporters, assert a successful request produces a `SERVER` span with `http.route`/`http.status_code`/duration, and that a `logger.info(..., extra={...})` call made during handling produces a log record whose `trace_id`/`span_id` match the span and whose `extra` keys appear as individual log-record attributes (contract §2)
- [X] T008 [P] [US1] Integration test in `src/backend/tests/integration/test_observability_login_failure.py`: force `/api/auth/login` (the spec's concrete regression case) to raise inside `_guarded()`, and assert an OTel exception span/log record pair is captured with matching `trace_id`/`span_id` — regression test for "login 500s not showing up in Application Insights" (contract §1, SC-002)
- [X] T009 [P] [US1] Unit test in `src/backend/tests/unit/test_observability_credential_exclusion.py`: send a request carrying a known fixture bearer token and password-like value through both a success and a failure path, then assert no captured span or log-record attribute equals or contains that literal value (FR-006, SC-004, contract §1)

### Implementation for User Story 1

- [X] T010 [US1] In `src/backend/function_app.py`'s `_guarded()` wrapper, ensure every caught exception both records the exception on the current OTel span (`span.record_exception(...)` / equivalent) and sets span status to `ERROR` before `logger.exception(...)` runs — do not rely solely on auto-instrumentation if T006/T008 show it isn't populating the exception event (FR-002)
- [X] T011 [US1] Verify (and if needed, explicitly configure in `src/backend/observability/setup.py`) that the `LoggingInstrumentor` used by `configure_azure_monitor()` attaches `trace_id`/`span_id` to every log record and preserves `extra` kwargs as individually queryable attributes, per T007's contract (FR-003, FR-008)
- [X] T012 [US1] Add/confirm a shared pytest fixture in `src/backend/tests/conftest.py` that installs OTel's `InMemorySpanExporter` and in-memory log exporter for the duration of a test, resetting them between tests, for reuse by T006–T009

**Checkpoint**: User Story 1 is fully functional and independently testable — backend telemetry is trustworthy on its own, before any frontend work begins.

---

## Phase 4: User Story 2 - An Engineer Can Trace a User Action End-to-End, Frontend Through Backend (Priority: P2)

**Goal**: Frontend page views, unhandled exceptions, and outbound API calls (including calls
that never reach the backend) are captured and, when they do reach the backend, correlate into
the same Application Insights trace as the backend's OTel spans.

**Independent Test**: Trigger a frontend action that calls a backend endpoint (e.g. login);
verify the frontend interaction, its outbound API call, and the backend request all correlate
under one `trace_id`.

### Tests for User Story 2

- [X] T013 [P] [US2] Test in `src/frontend/tests/observability/appInsights.test.js`: mock `@microsoft/applicationinsights-web`'s channel and assert the SDK is initialized exactly once at app startup with `distributedTracingMode: DistributedTracingModes.W3C` and `enableCorsCorrelation: true` (contract §3/§4)
- [X] T014 [P] [US2] Test in `src/frontend/tests/observability/errorBoundary.test.jsx`: render a component that throws inside the error boundary and assert an Exception event (message + stack trace) is reported to the mocked Application Insights channel (contract §3)
- [X] T015 [P] [US2] Test in `src/frontend/tests/observability/dependencyFailure.test.js`: mock an outbound `axios` call that fails before any response is received (simulated network error) and assert a Dependency-failure telemetry event is still emitted to the mocked channel, with no backend counterpart required (FR-005a, contract §3)
- [X] T016 [US2] Integration test in `src/backend/tests/integration/test_observability_correlation.py` and/or `src/frontend/tests/integration/`: trigger a simulated frontend→backend call carrying a `traceparent` header and assert the backend's captured span `trace_id` matches the incoming header's trace ID (contract §4, FR-005)

### Implementation for User Story 2

- [X] T017 [P] [US2] Create `src/frontend/src/observability/appInsights.js`: initialize `@microsoft/applicationinsights-web` with the connection string/instrumentation key from existing frontend config, `distributedTracingMode: DistributedTracingModes.W3C`, `enableCorsCorrelation: true`, and the `@microsoft/applicationinsights-react-js` plugin for route-change page views
- [X] T018 [US2] Update `src/frontend/src/index.jsx` to import and initialize `observability/appInsights.js` before `ReactDOM.createRoot(...).render(...)`
- [X] T019 [US2] Wire the React Router page-view plugin from `observability/appInsights.js` into the router in `src/frontend/src/App.jsx` (route-change → PageView telemetry, contract §3)
- [X] T020 [P] [US2] Create `src/frontend/src/observability/ErrorBoundary.jsx`: a React error boundary that reports caught render errors to Application Insights via `appInsights.trackException(...)` with message and stack trace
- [X] T021 [US2] Update `src/frontend/src/App.jsx` to use `observability/ErrorBoundary.jsx` (replacing or wrapping the existing `components/Common/ErrorBoundary.jsx`) so render errors are both shown to the user and reported as telemetry
- [X] T022 [US2] Add a global `window.onerror`/`window.onunhandledrejection` handler in `observability/appInsights.js` initialization (or confirm the SDK's default automatic exception tracking covers this) so unhandled JS errors outside the React tree are also captured (contract §3)

**Checkpoint**: All user stories are independently functional — an engineer can now trace a user action end-to-end, frontend through backend, in Application Insights.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation/verification pass confirming the feature's cross-cutting
guarantees hold across both stories.

- [X] T023 [P] Update `specs/013-opentelemetry-observability/quickstart.md`'s cross-cutting check by confirming (locally, via diff of `src/host.json`) that the host-level Application Insights log-forwarding path is removed, and note the result
- [X] T023a [P] Confirm FR-007 is satisfied without new code: verify `src/backend/services/llm_service.py`'s existing `gen_ai.*` spans still match the attribute names in `data-model.md`'s Telemetry Attribute Schema / contract §5 (prompt, response, input/output tokens, cost, latency), and note this confirmation in the PR description as this feature's FR-007 evidence
- [X] T024 Run the full backend and frontend test suites (`cd src/backend && python -m pytest tests/unit tests/integration`, `cd src/frontend && npm test`) to confirm no regressions were introduced by the observability wiring changes
- [ ] T025 Manual validation against the live deployed environment per quickstart.md's Principle IX final-acceptance steps (trigger a real backend error and a real frontend→backend action; confirm both in Application Insights) — record the outcome in the PR description, not in this repo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only — no dependency on User Story 2
- **User Story 2 (Phase 4)**: Depends on Foundational; its correlation tests (T016) additionally depend on User Story 1's backend span/log correlation (T010–T011) being correct, so implement US1 before US2 even though they touch disjoint files
- **Polish (Phase 5)**: Depends on both user stories being complete

### Within Each User Story

- Tests (T006–T009, T013–T016) before/alongside their corresponding implementation tasks — write them first per the template's TDD guidance and confirm they fail before T010–T012 / T017–T022 land
- Backend bootstrap/log correlation (T010–T011) before the correlation test that depends on it (T016)
- Frontend SDK initialization (T017–T018) before page-view/error-boundary/dependency wiring that depends on an initialized SDK instance (T019–T022)

### Parallel Opportunities

- T001 (package.json edit) can run alongside Phase 2's backend-only tasks
- All of T006–T009 (different test files) can run in parallel
- All of T013–T015 (different test files) can run in parallel
- T017 and T020 (different new files) can run in parallel; both must complete before T018/T019/T021/T022

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test in src/backend/tests/unit/test_observability_exceptions.py"
Task: "Unit test in src/backend/tests/unit/test_observability_success.py"
Task: "Integration test in src/backend/tests/integration/test_observability_login_failure.py"
Task: "Unit test in src/backend/tests/unit/test_observability_credential_exclusion.py"
```

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Test in src/frontend/tests/observability/appInsights.test.js"
Task: "Test in src/frontend/tests/observability/errorBoundary.test.jsx"
Task: "Test in src/frontend/tests/observability/dependencyFailure.test.js"

# Launch independent new-file implementation tasks together:
Task: "Create src/frontend/src/observability/appInsights.js"
Task: "Create src/frontend/src/observability/ErrorBoundary.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories)
3. Complete Phase 3: User Story 1 — backend telemetry is now trustworthy on its own
4. **STOP and VALIDATE**: run `cd src/backend && python -m pytest tests/unit tests/integration -k observability`, and manually confirm a forced backend error appears in Application Insights (quickstart.md US1 steps)
5. This alone resolves the spec's concrete motivating gap (login 500s invisible in Application Insights) — deployable as an increment

### Incremental Delivery

1. Setup + Foundational → backend OTel pipeline is the sole path to Application Insights
2. Add User Story 1 → validate independently → deploy/demo (MVP)
3. Add User Story 2 → validate independently (`cd src/frontend && npm test -- observability`, plus the live correlation check) → deploy/demo
4. Phase 5 polish and Principle IX final acceptance close out the feature
