# Feature Specification: OpenTelemetry Observability Instrumentation

**Feature Branch**: `013-opentelemetry-observability`

**Created**: 2026-08-29

**Status**: Draft

**Input**: User description: "OpenTelemetry observability instrumentation: instrument the Python Azure Functions backend and the ReactJS frontend using OpenTelemetry SDKs/APIs, with Azure Application Insights configured as the telemetry sink for traces, metrics, and logs, per Constitution Principle VI (Observability & AI Cost Transparency) and the Observability & Telemetry Requirements section. This replaces ad-hoc/backend-native logging (the Azure Functions host's built-in App Insights bridge, plain console logging on the frontend) with proper OTel instrumentation end to end: request/exception traces and structured logs from the backend (including unhandled-exception visibility, e.g. the current /api/auth/login 500s that aren't showing up in Application Insights), and equivalent frontend instrumentation. Future LLM-call telemetry (prompt/response capture, token usage, cost, latency per the constitution) should be accounted for in the design but does not need concrete LLM integration yet since no LLM calls exist in the codebase yet (that's 008-core-gameplay)."

## User Scenarios & Testing *(mandatory)*

<!--
  This is an infrastructure/platform feature rather than a player- or admin-facing one.
  The "users" here are the engineering team diagnosing production behavior; the value
  delivered is being able to trust Application Insights as the single place to answer
  "did this request succeed, and if not, why" without reproducing the issue locally or
  reading raw log files.
-->

### User Story 1 - An Engineer Can Diagnose a Failed Backend Request from Application Insights Alone (Priority: P1)

An engineer investigating a user-reported error (e.g., "I got an error logging in") opens Application Insights and finds the failed request, its exception with a full stack trace, and any log messages emitted while handling it — without needing local reproduction, SSH access, or raw log files.

**Why this priority**: This is the concrete gap that surfaced this feature: a backend exception during login currently produces a generic 500 with nothing queryable in Application Insights. Every other observability improvement in this feature builds on the backend actually emitting this telemetry in the first place.

**Independent Test**: Force a backend endpoint to raise an unhandled exception, then verify in Application Insights that the exception, its stack trace, and the originating request are all visible and linked, within normal Application Insights ingestion latency.

**Acceptance Scenarios**:

1. **Given** a request to any backend endpoint raises an unhandled exception, **When** the exception occurs, **Then** Application Insights records the exception with its full stack trace, linked to the request that triggered it.
2. **Given** a request completes successfully, **When** an engineer looks it up in Application Insights, **Then** they can see the request's outcome (status code, duration) and any structured log messages emitted while handling it.
3. **Given** a handler emits a log message at info, warning, or error severity, **When** that message is queried in Application Insights, **Then** it appears as structured telemetry (queryable by field, not only as opaque free text) and is attributed to the request/operation that produced it.

---

### User Story 2 - An Engineer Can Trace a User Action End-to-End, Frontend Through Backend (Priority: P2)

An engineer investigating a user-reported problem can follow a single user action — e.g., clicking "Sign in" — starting from the frontend interaction, through the API call it triggers, into the backend request that serves it, as one connected trace in Application Insights, rather than piecing together separate, uncorrelated frontend and backend telemetry.

**Why this priority**: Once the backend is emitting trustworthy telemetry (User Story 1), the next-highest-value gap is that frontend errors and slowness are currently invisible to the engineering team entirely, and even once visible, are useless for diagnosis if they can't be connected to the backend request they caused.

**Independent Test**: Trigger a frontend action that calls a backend endpoint (e.g., login), then verify in Application Insights that the frontend page view/interaction, its outbound API call, and the corresponding backend request all appear correlated under a single trace.

**Acceptance Scenarios**:

1. **Given** a user performs an action in the browser that calls a backend endpoint, **When** an engineer inspects that request in Application Insights, **Then** the frontend-side telemetry and the backend-side telemetry for that same action are linked together, not reported as unrelated events.
2. **Given** an unhandled JavaScript error occurs in the frontend, **When** it occurs, **Then** Application Insights records it with enough detail (message, stack trace, and the page/action it occurred during) for an engineer to diagnose it without needing the user to describe what happened.
3. **Given** a frontend API call fails or times out, **When** it happens, **Then** Application Insights shows the failure on the frontend side even if the backend never received or logged a corresponding request.

---

### User Story 3 - Observability Keeps Working When Application Insights Is Unavailable or Unconfigured (Priority: P3)

In local development (no Application Insights connection configured) or during a transient outage of the telemetry sink, the application continues to function normally — instrumentation never becomes a cause of failures or added latency for real users.

**Why this priority**: Observability tooling that can itself break the application defeats its purpose and creates deployment risk; this is a safety property that must hold across every environment the other two stories run in, but doesn't gate their core value.

**Independent Test**: Run the backend and frontend with no Application Insights connection string configured, and separately simulate the telemetry endpoint being unreachable; verify in both cases that normal application requests still succeed.

**Acceptance Scenarios**:

1. **Given** no Application Insights connection is configured, **When** the backend starts and serves requests, **Then** it runs normally and requests succeed, with telemetry simply not exported anywhere.
2. **Given** the Application Insights endpoint is unreachable from the frontend (e.g., blocked by network policy or an ad blocker), **When** a user uses the application, **Then** their experience is unaffected.

---

### Edge Cases

- What happens when the Application Insights daily data cap (already configured at 5 GB) is reached — does error/exception telemetry keep flowing, or does everything (including the traces engineers need most) get dropped indiscriminately?
- How does the system handle a burst of identical errors (e.g., a dependency outage causing every request to fail the same way) without either losing visibility into the failure or overwhelming the telemetry pipeline?
- What happens to a trace that starts on the frontend but whose backend leg fails before a response is returned (e.g., a network failure) — is the frontend-side failure still captured on its own?
- What happens when a request or log message would otherwise include a bearer token, password, or similar credential value — is it excluded from captured telemetry?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend MUST emit request, dependency, and exception telemetry using OpenTelemetry SDK instrumentation, exported to Azure Application Insights.
- **FR-002**: Every exception that reaches a backend route's top-level error handling MUST be captured as exception telemetry with a full stack trace, correlated to the request that triggered it — none may be silently converted to a generic error response with no corresponding telemetry.
- **FR-003**: Backend log messages (info, warning, error) MUST be emitted as structured OpenTelemetry log records correlated to the request/operation that produced them, not only as free-text log lines.
- **FR-004**: The frontend MUST emit page-view, unhandled-exception, and outbound API call telemetry using OpenTelemetry SDK instrumentation, exported to the same Azure Application Insights instance as the backend.
- **FR-005**: A user action that spans a frontend interaction and the backend request(s) it triggers MUST be correlated end-to-end in Application Insights via shared distributed-tracing context.
- **FR-006**: Telemetry MUST NOT include the value of bearer tokens, passwords, or other credential material, regardless of severity level or whether the containing request succeeded or failed.
- **FR-007**: The backend and frontend MUST continue serving requests normally if the Application Insights sink is unconfigured or unreachable; instrumentation MUST NOT be a cause of request failure or user-visible latency.
- **FR-008**: Exception and error-severity telemetry MUST be prioritized for retention over routine successful-request telemetry if data volume approaches the configured Application Insights daily cap, so diagnosing failures remains possible even under volume pressure.
- **FR-009**: The instrumentation design MUST accommodate attaching future LLM-call attributes (prompt, response, input/output token counts, computed cost, latency) to spans without a breaking schema change, even though no LLM call sites exist yet to instrument.
- **FR-010**: Existing backend log call sites MUST be preserved in content and meaning but routed through the OpenTelemetry logging pipeline rather than the Azure Functions host's built-in, non-OpenTelemetry Application Insights bridge.

### Key Entities

- **Trace/Span**: A single request or operation's timing, status, and metadata (e.g., one backend HTTP request, or one frontend page interaction), correlated across the frontend and backend when they belong to the same user action.
- **Log Record**: A structured, severity-leveled event (info/warning/error/exception) emitted during a trace/span, queryable by field rather than only as free text.
- **Telemetry Attribute Schema (forward-looking)**: The set of fields a future LLM-call span will carry (prompt, response, token usage, cost, latency) — defined now only to the extent needed to ensure today's instrumentation doesn't block adding it later; no LLM call sites are instrumented by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer can find a failed backend request's exception, full stack trace, and associated log messages in Application Insights within normal ingestion latency (a few minutes), with zero need to reproduce the issue locally or read raw log files.
- **SC-002**: 100% of unhandled exceptions across backend endpoints, observed in testing, appear as exception telemetry in Application Insights; zero are silently discarded into a generic error response with no corresponding telemetry.
- **SC-003**: An engineer can follow a single user action from its frontend interaction through to the backend request(s) it triggered as one correlated trace in Application Insights, with zero manual cross-referencing of separate log sources.
- **SC-004**: The backend and frontend function with 100% of normal request success rate when Application Insights is unconfigured or unreachable, observed in testing — zero requests fail or measurably slow down because of instrumentation.
- **SC-005**: Zero instances of credential material (tokens, passwords) appear in captured telemetry, observed across representative test traffic including failure paths.

## Assumptions

- Application Insights and its Log Analytics workspace are already provisioned (007-azure-infrastructure-provisioning); this feature instruments the application to use that existing sink, it does not provision new telemetry infrastructure.
- The existing Application Insights daily data cap (5 GB) and its connection string delivery to the Function App (via `site_config.application_insights_connection_string`) remain as currently configured; this feature does not need to change the underlying Azure resource, only how the application emits data to it.
- "Standard" OpenTelemetry semantic conventions (HTTP server/client spans, exception recording) are used wherever applicable, rather than inventing project-specific span/attribute names, so telemetry stays queryable using familiar Application Insights views (Failures, Performance, Application Map).
- Sensitive-value exclusion (FR-006) is achieved by never passing credential material into any telemetry API to begin with, rather than by post-hoc redaction/scrubbing of already-captured data.
- Since no LLM integration exists yet, this feature does not define the final prompt/response/cost telemetry schema in detail — it only ensures the chosen instrumentation approach (OpenTelemetry spans/attributes) is the right shape to extend later, per FR-009. Finalizing that schema is deferred to whichever feature first adds real LLM calls (008-core-gameplay).
- This feature migrates existing ad hoc `logging` call sites in the backend to flow through OpenTelemetry rather than deleting or renaming them; no behavior change is intended for what gets logged, only how it reaches Application Insights.
- Local development without an Application Insights connection string configured is expected to continue working exactly as it does today (per FR-007), consistent with how the rest of the backend already treats Azure-service configuration as optional/absent locally.
