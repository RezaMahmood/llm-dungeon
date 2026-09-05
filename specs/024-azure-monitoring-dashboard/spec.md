# Feature Specification: Azure Observability & Cost Dashboard

**Feature Branch**: `024-azure-monitoring-dashboard`

**Created**: 2026-09-05

**Status**: Draft

**Input**: User description: "as a cloud administrator I want to know what the state of my application and deployed infrastructure is. I want to see this as an Azure Dashboard. I already have Application Insights and application metrics being logged. I want to see failures, performance, traces and user statistics. this dashboard should be source controlled and deployed via github. availability is not required. I also want an estimated usage cost to show how much is being consumed by all resources in the llm-dungeon resource group"

## Clarifications

### Session 2026-09-05

- Q: Who or what should control who can view this Azure Dashboard, given it's a native Azure Portal resource rather than a page inside the application itself? → A: Azure RBAC role (e.g., Reader/Monitoring Reader) scoped to the `llm-dungeon` resource group, granted to the same people who administer that resource group today.
- Q: Does the cost panel need to show a breakdown by resource or resource type, or is a single aggregate total for the whole resource group enough? → A: Aggregate total only — one number for the whole `llm-dungeon` resource group.
- Q: What margin of error is acceptable between the dashboard's estimated cost and Azure's actual billed cost for the same period? → A: ±10% of actual billed cost for the period.
- Q: How fresh does the failure/performance/user-statistics data need to be — auto-refresh on a schedule, or current data whenever opened/reloaded? → A: Dashboard MUST auto-refresh on a defined interval (every 5 minutes) while open.
- Q: For the traces/dependency-calls panel, does the administrator need a searchable/filterable view of individual trace records, or is a summary view sufficient? → A: Summary view (top N slowest/failing dependencies over the time window), with a link to the full Application Insights trace details for further investigation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Application Failures at a Glance (Priority: P1)

As a cloud administrator, I want a single dashboard view showing current and recent
application failures (errors, exceptions, failed requests) so I can quickly tell whether
the application is healthy or something needs attention, without having to dig through
individual Application Insights blades.

**Why this priority**: Failure visibility is the most time-sensitive need — it is what
an administrator checks first when something seems wrong, and it delivers value even if
no other dashboard section exists yet.

**Independent Test**: Can be fully tested by opening the dashboard and confirming it
shows failed request counts, exception counts/types, and error trends over a recent time
window (e.g., last 24 hours), reflecting data already being logged to Application
Insights.

**Acceptance Scenarios**:

1. **Given** the application has logged failed requests or exceptions within the
   selected time window, **When** the administrator opens the dashboard, **Then** the
   failure counts and trend are visibly displayed and match what Application Insights
   records for that window.
2. **Given** the application has had zero failures in the selected time window, **When**
   the administrator opens the dashboard, **Then** the dashboard clearly shows a
   zero/healthy state rather than an empty or broken-looking panel.

---

### User Story 2 - Understand Performance and Request Traces (Priority: P2)

As a cloud administrator, I want to see performance metrics (response times, throughput)
and request/dependency traces so I can identify slow operations or bottlenecks in the
application.

**Why this priority**: Once failures are visible, understanding *why* the system is slow
or degraded (as opposed to fully broken) is the next most valuable diagnostic capability.

**Independent Test**: Can be fully tested by opening the dashboard and confirming it
shows response time / latency trends, request throughput, and a view into recent
traces or dependency calls sourced from Application Insights.

**Acceptance Scenarios**:

1. **Given** the application has processed requests within the selected time window,
   **When** the administrator opens the dashboard, **Then** average/percentile response
   time and throughput are displayed for that window.
2. **Given** a dependency (e.g., an external call the application makes) is slow or
   failing, **When** the administrator views the traces section, **Then** that
   dependency appears in a top-N slowest/failing summary distinguishable from normal
   calls, with a link to the full Application Insights trace details for further
   investigation.

---

### User Story 3 - Review User Statistics (Priority: P3)

As a cloud administrator, I want to see statistics about how the application is being
used (e.g., active users, session activity, usage trends over time) so I can understand
adoption and usage patterns alongside technical health.

**Why this priority**: Usage statistics provide business/adoption context but are not
needed to diagnose or respond to an incident, making this lower priority than failures
and performance.

**Independent Test**: Can be fully tested by opening the dashboard and confirming it
shows a count of active users/sessions over a selected time window, sourced from
application metrics already being logged.

**Acceptance Scenarios**:

1. **Given** users have interacted with the application within the selected time window,
   **When** the administrator opens the dashboard, **Then** user/session activity counts
   and a trend over time are displayed.

---

### User Story 4 - See Estimated Resource Group Cost (Priority: P4)

As a cloud administrator, I want to see an estimated usage cost for all resources in the
`llm-dungeon` resource group so I can track spend alongside application health.

**Why this priority**: Cost visibility is valuable for ongoing budget awareness but is
independent of, and less urgent than, understanding whether the application itself is
healthy and performing well.

**Independent Test**: Can be fully tested by opening the dashboard and confirming it
shows a single estimated cost total covering all resources currently deployed in the
`llm-dungeon` resource group.

**Acceptance Scenarios**:

1. **Given** resources are deployed in the `llm-dungeon` resource group and have accrued
   usage, **When** the administrator opens the dashboard, **Then** an estimated cost
   figure covering that resource group is displayed.
2. **Given** a new resource is added to or removed from the `llm-dungeon` resource
   group, **When** cost data next refreshes, **Then** the displayed estimate reflects the
   updated set of resources without manual dashboard reconfiguration.

---

### Edge Cases

- What happens when Application Insights has no data yet for a given panel (e.g., a
  brand-new metric or a quiet time window)? Dashboard MUST show an explicit
  empty/no-data state rather than an error or blank panel.
- What happens when cost data for the current billing period is incomplete or delayed
  (a common characteristic of cloud cost/usage data)? Dashboard MUST label the figure as
  an estimate and indicate the time period it covers.
- How does the dashboard behave immediately after a redeploy from source control (e.g.,
  panel layout changes)? The redeployed dashboard MUST fully replace the previous
  version's layout without leaving orphaned or duplicate panels.
- What happens if a resource is removed from the `llm-dungeon` resource group entirely?
  Cost and health panels MUST stop referencing that resource going forward rather than
  showing stale data indefinitely.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single Azure Dashboard that surfaces the current
  state of the application and its deployed infrastructure for the `llm-dungeon`
  environment.
- **FR-002**: Dashboard MUST display application failure data (failed request counts,
  exception counts and types, and error trends over a recent time window) sourced from
  the existing Application Insights instance.
- **FR-003**: Dashboard MUST display performance data (response time/latency and request
  throughput trends over a recent time window) sourced from existing application
  metrics.
- **FR-004**: Dashboard MUST display a summary of the top N slowest and/or failing
  request/dependency traces over the selected time window, each with a link to the
  corresponding Application Insights trace details for further investigation, so an
  administrator can identify which operations or dependencies are slow or failing.
- **FR-005**: Dashboard MUST display user statistics (active users and/or session
  activity, with a trend over a recent time window) sourced from existing application
  metrics.
- **FR-006**: Dashboard MUST display an estimated usage cost covering all resources
  currently in the `llm-dungeon` resource group, labeled with the time period the
  estimate covers.
- **FR-007**: Dashboard MUST NOT include an availability/uptime status panel — the user
  has explicitly excluded availability monitoring from this feature's scope.
- **FR-008**: The dashboard's definition (layout, panels, queries/configuration) MUST be
  stored as version-controlled files in this repository rather than being manually
  configured only in the Azure portal.
- **FR-009**: The dashboard MUST be deployed and updated in the `llm-dungeon` Azure
  environment via an automated GitHub-based pipeline, so that a change committed to the
  dashboard definition is reflected in the live dashboard without a manual portal edit.
- **FR-010**: Each dashboard panel MUST clearly indicate what data it shows and the time
  window it covers, so an administrator can interpret the state at a glance.
- **FR-011**: Access to the dashboard MUST be restricted via an Azure RBAC role (e.g.,
  Reader or Monitoring Reader) scoped to the `llm-dungeon` resource group, granted to
  the same people who already administer that resource group, rather than a
  separately-maintained access list.
- **FR-012**: The failure, performance, and user-statistics panels MUST auto-refresh on a
  5-minute interval while the dashboard is open, so an administrator viewing it sees
  current data without manually reloading.

### Key Entities

- **Dashboard Definition**: The version-controlled description of the dashboard's
  layout and panels (what each panel shows and which data source/time window it uses).
  Deployed automatically to become the live Azure Dashboard.
- **Failure Metric**: A count or rate of failed requests/exceptions over a time window,
  sourced from Application Insights.
- **Performance Metric**: A response-time, latency, or throughput measurement over a
  time window, sourced from existing application metrics.
- **Trace/Dependency Record**: Data about an individual request's execution path or an
  outbound dependency call, including duration and success/failure.
- **User Statistic**: A count or trend of active users/sessions over a time window,
  sourced from existing application metrics.
- **Resource Group Cost Estimate**: An aggregated, time-bounded estimate of usage cost
  across all resources in the `llm-dungeon` resource group.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A cloud administrator can determine whether the application currently has
  failures, and roughly how severe they are, within 10 seconds of opening the dashboard.
- **SC-002**: A cloud administrator can identify the current response-time/performance
  trend and locate a slow trace/dependency without leaving the dashboard.
- **SC-003**: A cloud administrator can view current user activity statistics and an
  estimated cost for the `llm-dungeon` resource group from the same single dashboard,
  without needing to query separate Azure portal blades.
- **SC-004**: A change to the dashboard definition committed to source control is
  reflected in the live Azure Dashboard without any manual configuration step in the
  Azure portal.
- **SC-005**: The estimated resource group cost shown on the dashboard stays within ±10%
  of the actual cost reported by Azure Cost Management for the same period (accepting
  that cloud cost/usage data is inherently an estimate with reporting delay).

## Assumptions

- "State of my application and deployed infrastructure" is interpreted as: failures,
  performance, traces, and user statistics (as explicitly listed by the user) plus
  resource group cost — not availability/uptime, which the user explicitly excluded.
- All required telemetry (failures, performance, traces, user activity) is already being
  logged to the existing Application Insights instance and application metrics, per the
  user's statement; this feature surfaces that existing data rather than adding new
  instrumentation.
- "Estimated usage cost" refers to Azure's own cost/usage data for the resource group
  (which is inherently an estimate, subject to short reporting delay) rather than a
  custom cost-prediction model.
- The relevant scope is the single `llm-dungeon` resource group; the dashboard does not
  need to cover resources outside that resource group.
- Dashboard access is governed by Azure RBAC (a role such as Reader or Monitoring Reader
  scoped to the `llm-dungeon` resource group), granted to the resource group's existing
  administrators — not by the application's own Entra ID sign-in/allow-list, which
  governs the application itself rather than native Azure Portal resources.
- A "recent time window" default (e.g., last 24 hours, with the ability to adjust) is
  acceptable for failure/performance/user-statistic panels unless a specific reporting
  window is later required.
