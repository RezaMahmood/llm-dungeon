# Feature Specification: Observability Resilience

**Feature Branch**: `018-observability-resilience`

**Created**: 2026-08-29

**Status**: Draft

**Input**: Split out of `013-opentelemetry-observability` on 2026-08-29, so that spec covers at most two user stories. This spec covers the third user story originally specified there — "Observability Keeps Working When Application Insights Is Unavailable or Unconfigured" — along with the data-volume-pressure and error-burst edge cases that originally accompanied it.

**Split**: This spec depends on `013-opentelemetry-observability` for the OpenTelemetry instrumentation whose failure modes it specifies safeguards for; it adds no new telemetry of its own.

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

---

### Edge Cases

- What happens when the Application Insights daily data cap (already configured at 5 GB) is reached — does error/exception telemetry keep flowing, or does everything (including the traces engineers need most) get dropped indiscriminately?
- How does the system handle a burst of identical errors (e.g., a dependency outage causing every request to fail the same way) without either losing visibility into the failure or overwhelming the telemetry pipeline?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend and frontend MUST continue serving requests normally if the Application Insights sink is unconfigured or unreachable; instrumentation MUST NOT be a cause of request failure or user-visible latency.
- **FR-002**: Exception and error-severity telemetry MUST be prioritized for retention over routine successful-request telemetry if data volume approaches the configured Application Insights daily cap, so diagnosing failures remains possible even under volume pressure.
- **FR-003**: Each distinct resilience outcome (normal operation with no Application Insights connection configured, normal operation when the sink is unreachable, and retention prioritization under data-volume pressure) MUST have a corresponding automated check verifying its expected behavior.

### Key Entities

- **Telemetry Sink Availability**: Whether Application Insights is configured and reachable at a given moment; this spec defines the behavior instrumentation from `013-opentelemetry-observability` must fall back to when it is not.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The backend and frontend function with 100% of normal request success rate when Application Insights is unconfigured or unreachable, observed in testing — zero requests fail or measurably slow down because of instrumentation.

## Assumptions

- The existing Application Insights daily data cap (5 GB) and its connection string delivery to the Function App (via `site_config.application_insights_connection_string`) remain as currently configured; this feature does not need to change the underlying Azure resource, only how instrumentation degrades gracefully around its limits.
- Local development without an Application Insights connection string configured is expected to continue working exactly as it does today, consistent with how the rest of the backend already treats Azure-service configuration as optional/absent locally.
