# Research: Azure Observability & Cost Dashboard

## 1. Dashboard resource type

- **Decision**: Define the dashboard as a Terraform `azurerm_portal_dashboard`
  resource (`Microsoft.Portal/dashboards`), in a new
  `infrastructure/terraform/dashboard.tf`, in the same pre-existing
  `llm-dungeon` Resource Group as every other resource (`data.azurerm_resource_group.rg`).
- **Rationale**: `azurerm_portal_dashboard` is already in the `hashicorp/azurerm`
  provider version this project pins (`>= 3.80.0`), so no new provider or
  `azapi` dependency is needed. Its `dashboard_properties` argument takes the
  same JSON shape as an exported Azure Portal dashboard, so panels can be
  authored/verified interactively in the portal and then captured as the
  Terraform JSON payload — a well-trodden path for this resource type.
- **Alternatives considered**: `azapi_resource` targeting
  `Microsoft.Portal/dashboards` directly — rejected, adds a second Terraform
  provider for no capability `azurerm_portal_dashboard` doesn't already cover.
  An Azure Monitor Workbook as the *primary* surface instead of a Dashboard —
  rejected because the spec explicitly asks for "an Azure Dashboard."

## 2. Failure / performance / user-statistics panels (FR-002, FR-003, FR-005, FR-012)

- **Decision**: Use Azure Portal Dashboard "Monitor Chart" parts
  (`Extension/HubsExtension/PartType/MonitorChartPart`) bound directly to the
  existing `azurerm_application_insights.appinsights` resource's standard
  metrics: `requests/failed`, `exceptions/count`, `requests/duration`,
  `requests/count` (throughput). User statistics (active users/sessions) use
  a Log query chart part (`LogsDashboardPart`) running a KQL query against the
  same Application Insights resource's `customEvents`/`pageViews` stream
  (whatever the app already emits per Constitution Principle VI's OTel→App
  Insights pipeline), since "active users" isn't a standard platform metric.
  All of these parts natively support the Portal's own auto-refresh setting.
- **Rationale**: Metrics/Logs dashboard parts are native Azure Dashboard
  building blocks purpose-built for exactly this ("pin a chart from App
  Insights to a dashboard"), require no additional compute/Function to poll
  and republish data, and read directly from the existing telemetry — no new
  instrumentation, matching the spec's assumption that all required telemetry
  already exists.
- **Refresh (FR-012)**: The dashboard resource's top-level JSON carries a
  `metadata.model.timeRange` plus a portal-native auto-refresh interval;
  `dashboard_properties` sets this to 5 minutes so the failure/performance/
  user-statistics parts refresh unattended while the dashboard is open,
  satisfying FR-012 without any custom polling code.
- **Alternatives considered**: A custom Function that queries App Insights on
  a timer and writes to a custom store for the dashboard to read — rejected
  as unnecessary complexity (Principle IV/XII): native dashboard parts already
  do this.

## 3. Traces / dependency summary panel (FR-004)

- **Decision**: A `LogsDashboardPart` KQL query part against
  `azurerm_application_insights.appinsights`, e.g. a "top N slowest/failing
  dependencies over the window" query against the `dependencies` table
  (`summarize` by `name`/`target`, ordered by `avg(duration)` desc and by
  failure rate), rendered as a table. The part's query includes a markdown
  link (or the part's own "open in Application Insights" affordance) pointing
  to the App Insights resource's Transaction Search / Failures blade, scoped
  to the same resource, for the "further investigation" requirement.
- **Rationale**: Matches the clarified requirement exactly (summary view, not
  a full searchable trace explorer) and reuses the same Log Analytics-backed
  query mechanism as the user-statistics panel — one query pattern, not two.
- **Alternatives considered**: Embedding a full Application Insights
  "Application Map" or "Transaction Search" part inline — rejected; the
  clarification explicitly scoped this to a top-N summary plus a link out.

## 4. Resource Group cost panel (FR-006, SC-005)

- **Decision**: An Azure Monitor Workbook, defined as a Terraform
  `azurerm_application_insights_workbook` (or, if the cost query type isn't
  supported by that resource's `data_json`, a lightweight custom Workbook
  resource under the same Terraform config), scoped to the `llm-dungeon`
  Resource Group, using a Workbook query of type `Azure Resource Graph` /
  Cost Management (`microsoft.costmanagement/query`, ActualCost, grouped by
  none — a single aggregate total) for the current billing period-to-date.
  The workbook is pinned onto the dashboard as a `WorkbookPinnedPart`. The
  panel's markdown title states the covered time period and that the figure
  is an estimate (per the Edge Cases requirement).
- **Rationale**: Azure Cost Management's own data is the "estimated usage
  cost" the spec asks for (per Assumptions) — Cost Management's actual/
  amortized cost query, aggregated with no grouping dimension, is by
  definition the whole resource group's total and stays automatically
  in sync as resources are added/removed (FR-006 acceptance scenario 2),
  with no per-resource maintenance. A Workbook is the standard Azure-native
  way to embed a Cost Management query as a dashboard-pinnable visual;
  there is no first-class "Cost" dashboard part type outside a Workbook.
  The ±10% accuracy bound (SC-005) is inherent to Azure's own Cost Management
  data (subject to short billing-reconciliation delay) — this feature reads
  that data as-is rather than building a custom estimator, so no additional
  work is needed to hit the bound.
- **Refresh**: Not subject to FR-012's 5-minute requirement (that FR is
  scoped to failure/performance/user-statistics panels only); a pinned
  Workbook part refreshes when the dashboard is opened/reloaded, which
  satisfies the "current data whenever opened" bar the clarification set
  for panels outside the 5-minute-refresh set, and matches Cost Management's
  own update cadence (roughly daily), so a tighter refresh would show no
  new data anyway.
- **Alternatives considered**: A custom Function polling the Cost Management
  REST API on a timer and writing to a store the dashboard reads — rejected
  as unneeded complexity (Principle IV/XII) given a Workbook can query Cost
  Management directly and natively.

## 5. Access control (FR-011)

- **Decision**: No new Terraform role assignment resource. Document (in
  `docs/INFRASTRUCTURE.md` and this dashboard's own README/quickstart) that
  because the dashboard is an ordinary resource inside the `llm-dungeon`
  Resource Group, anyone already holding Reader, Monitoring Reader, Owner, or
  Contributor on that Resource Group can already open it — the same people
  who administer the group today, with no separate access list to maintain.
- **Rationale**: This project's existing RG-level administrator access is
  granted out-of-band (outside Terraform state), the same way the GitHub
  OIDC Managed Identity's Contributor role assignment is granted via
  `infrastructure/scripts/bootstrap.sh` rather than a Terraform resource, per
  `identity.tf`'s own comment. Adding a parallel Terraform-managed role
  assignment here would create a second, competing place access is defined —
  exactly the "separately-maintained access list" the clarification rejected.
  Standard Azure RBAC already makes any Resource Group resource (including a
  Dashboard) visible to anyone with a role on that group; no dashboard-specific
  grant is technically required.
- **Alternatives considered**: A new `azurerm_role_assignment` granting
  Monitoring Reader at the Resource Group scope to a named set of principals —
  rejected: this project has no existing Terraform-managed admin-group
  variable to attach it to, and introducing one here would be new RBAC
  surface not requested by the spec (Principle XII: no elaborate role/
  permission hierarchies beyond what's already there).

## 6. Deployment pipeline (FR-008, FR-009, SC-004)

- **Decision**: No new pipeline. The dashboard is just another resource in
  `infrastructure/terraform/`, so it deploys through the existing
  `terraform-validate.yml` (PR checks) and `infrastructure-deploy.yml` (CD:
  manual `workflow_dispatch`, `production-infra` environment, human-approval
  gated) workflows already described in `docs/INFRASTRUCTURE.md`.
- **Rationale**: This satisfies FR-008 (version-controlled definition) and
  FR-009/SC-004 (a change reflected in the live dashboard via GitHub-based
  pipeline, no manual portal edit) with zero new infrastructure, consistent
  with Principle XII and the project's existing "no dedicated test/staging
  cloud environment" stance (Environments & Deployment Pipeline). Because
  `azurerm_portal_dashboard`'s full `dashboard_properties` is authoritative,
  a `terraform apply` fully replaces the previous layout (Edge Case:
  redeploy leaves no orphaned/duplicate panels) — Terraform sets the whole
  JSON document each apply, it does not merge.
- **Alternatives considered**: A separate GitHub Actions workflow dedicated
  to the dashboard — rejected; would duplicate `infrastructure-deploy.yml`'s
  validate → plan → apply shape for no new requirement.

## 7. Testing approach (Constitution Principle I)

- **Decision**: Extend `infrastructure/tests/test_resource_creation.py` (or a
  new `test_dashboard.py` alongside it) with a post-apply check that the
  `Microsoft.Portal/dashboards` resource exists in the `llm-dungeon` group
  with the expected name, plus a `terraform validate`/plan-time check
  (already covered by `test_terraform_validate.sh`) that the dashboard JSON
  is well-formed. Panel-level correctness (do the KQL queries return sane
  data) is not unit-testable without live App Insights data and is verified
  via `quickstart.md`'s manual validation steps instead — consistent with
  how this project already treats infrastructure resource existence
  (automated) versus live behavior (quickstart-verified), and with
  Principle IX's non-blocking playtesting stance for anything beyond
  automated resource-existence checks.
- **Alternatives considered**: Asserting exact panel query results in an
  automated test — rejected; would require seeding live telemetry data,
  which this project has no mechanism for and which Principle I does not
  require (tests exercise meaningful behavior, not full data-dependent
  content).
