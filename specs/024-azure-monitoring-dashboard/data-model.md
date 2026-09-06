# Data Model: Azure Observability & Cost Dashboard

This feature adds no application data model — it is an infrastructure
resource. The entities below (from `spec.md`'s Key Entities) map to
Terraform/Azure constructs rather than database records.

## Dashboard Definition

- **Represents**: The version-controlled description of the dashboard's
  layout and panels.
- **Terraform construct**: `azurerm_portal_dashboard.dashboard` in
  `infrastructure/terraform/dashboard.tf`, named
  `${local.name_prefix}dash${local.name_suffix}` (e.g. `llmdungeon-dash-prod`),
  scoped to `data.azurerm_resource_group.rg`, tagged with `local.common_tags`.
- **Fields**: `dashboard_properties` (JSON string: `lenses` → `parts`, one
  entry per panel below), `location` (matches the Resource Group's region).
- **Lifecycle**: Full-replace on every `terraform apply` — the JSON document
  is authoritative, so a redeploy never leaves orphaned/duplicate panels
  (Edge Case in spec.md).
- **Relationships**: Composed of one part per Failure/Performance/Trace/User
  Statistic/Cost entity below; each part references the Application Insights
  resource (or, for cost, the Workbook) it reads from by resource ID.

## Failure Metric

- **Represents**: Failed request counts, exception counts/types, error trend
  over a recent time window.
- **Source**: `azurerm_application_insights.appinsights` standard metrics
  `requests/failed` and `exceptions/count`.
- **Dashboard construct**: One `MonitorChartPart` per metric, time range
  bound to the panel's configured window (default last 24h, FR-002),
  auto-refresh 5 minutes (FR-012).
- **Empty state**: Metrics charts render a zero-value flat line rather than
  an error when no data exists in the window — satisfies the "explicit
  zero/healthy state" edge case natively (no custom empty-state code needed).

## Performance Metric

- **Represents**: Response time/latency and throughput trends.
- **Source**: `requests/duration` (avg + percentiles) and `requests/count`
  standard metrics on the same Application Insights resource.
- **Dashboard construct**: `MonitorChartPart`, same refresh/window rules as
  Failure Metric.

## Trace/Dependency Record

- **Represents**: An individual request's execution path or outbound
  dependency call (duration, success/failure), summarized as top-N
  slowest/failing over the window, with a link to full trace details.
- **Source**: The `dependencies` table in the Application Insights-backed
  Log Analytics workspace (`azurerm_log_analytics_workspace.logs`).
- **Dashboard construct**: `LogsDashboardPart` running a KQL summary query
  (top N by duration desc / by failure, over the panel's window), rendered
  as a table; the part links out to the Application Insights Transaction
  Search blade for the same resource for full-record investigation
  (FR-004).

## User Statistic

- **Represents**: Active users/session activity count and trend.
- **Source**: `customEvents`/`pageViews` (or whichever existing custom
  telemetry the application already emits for user activity) in the same
  Log Analytics workspace.
- **Dashboard construct**: `LogsDashboardPart` KQL query (distinct user/
  session count over time, bucketed), 5-minute auto-refresh (FR-012).

## Resource Group Cost Estimate

- **Represents**: An aggregated, time-bounded estimate of usage cost across
  all resources in `llm-dungeon`, labeled with the covered period.
- **Source**: Azure Cost Management's `ActualCost` query
  (`microsoft.costmanagement/query`), scoped to the `llm-dungeon` Resource
  Group ID, with no grouping dimension (single aggregate total per the
  clarification).
- **Dashboard construct**: An Azure Monitor Workbook resource
  (`infrastructure/terraform/dashboard.tf`, alongside the dashboard) holding
  the Cost Management query, pinned onto the Dashboard via a
  `WorkbookPinnedPart`. The panel's markdown/title explicitly states the
  billing period covered and that the figure is an estimate (Edge Case:
  incomplete/delayed cost data).
- **Update behavior**: Reflects resources currently in the Resource Group
  automatically on next refresh (no per-resource Terraform config), since
  the Cost Management query is scoped by Resource Group ID, not an
  enumerated resource list (FR-006 acceptance scenario 2; Edge Case: a
  removed resource stops being referenced without manual reconfiguration).
