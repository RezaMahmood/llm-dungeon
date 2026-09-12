# Feature Specification: Observability Resilience

**Feature Branch**: `018-observability-resilience`

**Created**: 2026-08-29

**Status**: Draft

**Input**: Split out of `013-opentelemetry-observability` on 2026-08-29, so that spec covers at most two user stories. This spec covers the third user story originally specified there — "Observability Keeps Working When Application Insights Is Unavailable or Unconfigured" — along with the data-volume-pressure and error-burst edge cases that originally accompanied it.

**Split**: This spec depends on `013-opentelemetry-observability` for the OpenTelemetry instrumentation whose failure modes it specifies safeguards for; it adds no new telemetry of its own.

## Clarifications

### Session 2026-09-12

- Q: How should the system decide when to start favouring error telemetry over routine successful-request telemetry — always, or only once usage nears the 5 GB daily cap? (FR-002) → A: Always on — exceptions and error-severity telemetry always exported in full; routine successful-request telemetry sampled down to a fixed lower rate at all times, with no live usage monitoring.
- Q: When a dependency outage makes every request fail the same way, should each of those identical errors be reported individually, or should repeats be collapsed into a count so the telemetry pipeline isn't flooded? → A: Report every error individually — no burst-specific suppression, de-duplication, or per-window limit; a deliberate decision justified by this application's scale.
- Q: If the Application Insights connection string is present but malformed or invalid, should the application start normally with telemetry switched off, or refuse to start so the misconfiguration is caught immediately? (FR-001) → A: Start normally with telemetry disabled, recording the initialization failure in the application's own local logs; never fail startup.
- Q: Should the reduced sampling of routine telemetry apply to browser-side telemetry as well as backend telemetry, and should a single user action be kept or dropped as a whole? (FR-002) → A: Both legs, decided once per user action — the browser decides and the backend honours that decision, so a routine trace is never half-present; errors stay exported in full on both sides.
- Q: While the telemetry endpoint is unreachable, what should happen to telemetry the application is trying to send — should it be held and retried, and can sending it ever delay a user's response? (FR-001, SC-001) → A: Sending telemetry never sits between a request and its response; telemetry awaiting delivery is held in a bounded buffer and excess is discarded rather than growing memory or blocking; any shutdown flush is time-limited.

## User Scenarios & Testing *(mandatory)*

<!--
  This is an infrastructure/platform feature rather than a player- or admin-facing one.
  The "users" here are real end users of the application and the engineering team; the
  value delivered is a safety guarantee that observability tooling never becomes a cause
  of application failure or degraded experience, in any environment.
-->

### User Story 1 - Observability Keeps Working When Application Insights Is Unavailable or Unconfigured (Priority: P1)

In local development (no Application Insights connection configured) or during a transient outage of the telemetry sink, the application continues to function normally — instrumentation never becomes a cause of failures or added latency for real users.

**Why this priority**: Observability tooling that can itself break the application defeats its purpose and creates deployment risk; this is a safety property that must hold across every environment `013-opentelemetry-observability`'s instrumentation runs in.

**Independent Test**: Run the backend and frontend with no Application Insights connection string configured, and separately simulate the telemetry endpoint being unreachable; verify in both cases that normal application requests still succeed.

**Acceptance Scenarios**:

1. **Given** no Application Insights connection is configured, **When** the backend starts and serves requests, **Then** it runs normally and requests succeed, with telemetry simply not exported anywhere.
2. **Given** the Application Insights endpoint is unreachable from the frontend (e.g., blocked by network policy or an ad blocker), **When** a user uses the application, **Then** their experience is unaffected.
3. **Given** local development with no Application Insights connection string configured, **When** the backend runs, **Then** it behaves exactly as it does today, consistent with how the rest of the backend already treats Azure-service configuration as optional/absent locally.
4. **Given** an Application Insights connection string that is present but malformed or invalid, **When** the backend or frontend starts, **Then** it starts and serves requests exactly as it does when no connection string is configured, with the initialization failure recorded in the application's own local logs rather than causing startup to fail.

---

### Edge Cases

- When data volume presses against the Application Insights daily data cap (already configured at 5 GB), telemetry MUST NOT be dropped indiscriminately: the constant prioritization in FR-002 keeps exception and error-severity telemetry — the traces engineers need most — flowing in full, with routine successful-request telemetry absorbing the reduction instead.
- A burst of identical errors (e.g., a dependency outage causing every request to fail the same way) is reported in full, one telemetry item per occurrence — visibility into the failure is never traded away to protect the pipeline. See FR-002a for why no suppression is applied.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend and frontend MUST continue serving requests normally if the Application Insights sink is unconfigured, configured with a malformed or invalid connection string, or unreachable; instrumentation MUST NOT be a cause of request failure or user-visible latency.
- **FR-001a**: A connection string that is present but malformed or invalid MUST NOT cause startup to fail. Telemetry initialization MUST degrade to the same disabled state as an absent connection string, and the initialization failure MUST be recorded in the application's own local logs so the misconfiguration is not silently invisible.
- **FR-001b**: Telemetry export MUST NOT sit between a request and its response — a response MUST NOT wait on a telemetry send, succeeding or failing. Telemetry awaiting delivery MUST be held in a bounded buffer; once that buffer is full, excess telemetry MUST be discarded rather than growing memory without limit or blocking application work. Any flush of pending telemetry at shutdown MUST be time-limited. Telemetry discarded this way is an accepted loss, not a failure condition.
- **FR-002**: Exception and error-severity telemetry MUST always be exported in full, while routine successful-request telemetry MUST be sampled down to a fixed lower rate at all times. This prioritization MUST be constant — it MUST NOT depend on monitoring current ingestion volume against the Application Insights daily cap — so that diagnosing failures remains possible under volume pressure and the behavior is identical, and locally verifiable, in every environment.
- **FR-002a**: Error telemetry MUST NOT be suppressed, de-duplicated, collapsed into counts, or rate-limited during a burst of identical errors; every occurrence MUST be reported individually. This is a deliberate decision, not an unspecified gap: preserving failure visibility outweighs protecting the telemetry pipeline at this application's request volume (see Assumptions).
- **FR-002b**: FR-002's sampling of routine successful-request telemetry MUST apply to both the backend and the browser. The keep-or-drop decision for a single user action MUST be made once, by the browser leg that starts the trace, and honoured by the backend request(s) it triggers, so a routine trace is never recorded with only one of its two halves. Exception and error-severity telemetry is exempt from sampling on both sides (FR-002).
- **FR-003**: Each distinct resilience outcome (normal operation with no Application Insights connection configured, normal operation with a malformed or invalid connection string, normal operation when the sink is unreachable, bounded buffering with no response ever waiting on a telemetry send, and the constant retention prioritization of FR-002) MUST have a corresponding automated check verifying its expected behavior.

### Key Entities

- **Telemetry Sink Availability**: Whether Application Insights is configured, validly configured, and reachable at a given moment — three independent ways the sink can be unusable (absent connection string, malformed connection string, unreachable endpoint). This spec defines the behavior instrumentation from `013-opentelemetry-observability` must fall back to in each case; all three fall back to the same disabled state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The backend and frontend function with 100% of normal request success rate when Application Insights is unconfigured, configured with a malformed or invalid connection string, or unreachable, observed in testing — zero requests fail because of instrumentation, and zero responses wait on a telemetry send.
- **SC-002**: 100% of exception and error-severity telemetry is exported, observed in testing, including during a burst of identical errors and while routine successful-request telemetry is being sampled down.
- **SC-003**: Zero routine traces are recorded with only one of their two halves (browser without backend, or backend without browser) as a result of sampling, observed across representative test traffic.
- **SC-004**: Memory held for pending telemetry stays within its configured bound throughout a sustained telemetry-endpoint outage, observed in testing — it does not grow without limit for as long as the sink stays unreachable.

## Assumptions

- The existing Application Insights daily data cap (5 GB) and its connection string delivery to the Function App (via `site_config.application_insights_connection_string`) remain as currently configured; this feature does not need to change the underlying Azure resource, only how instrumentation degrades gracefully around its limits.
- Local development without an Application Insights connection string configured is expected to continue working exactly as it does today, consistent with how the rest of the backend already treats Azure-service configuration as optional/absent locally.
- This is a private application serving an explicit allow-list of accounts, so request volume — and therefore the size of any error burst — is bounded well below what could overwhelm the telemetry pipeline or exhaust the 5 GB daily cap on error telemetry alone. FR-002a's no-suppression decision rests on that; a burst-suppression mechanism would be added only if a stated requirement called for one.
