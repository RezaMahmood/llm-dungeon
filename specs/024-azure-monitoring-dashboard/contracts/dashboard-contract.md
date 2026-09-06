# Contract: Azure Dashboard Definition

This feature's only external interface is the dashboard's own definition —
the JSON contract Terraform submits to `Microsoft.Portal/dashboards`, and the
queries each panel runs against existing data sources. There is no API
surface, CLI, or library contract to define.

## Dashboard resource contract

- **Resource**: `Microsoft.Portal/dashboards` (Terraform:
  `azurerm_portal_dashboard`), one instance, in the `llm-dungeon` Resource
  Group.
- **Name**: `${local.name_prefix}dash${local.name_suffix}` (matches the
  existing naming convention in `locals.tf`).
- **`dashboard_properties` shape**: `{ "lenses": { "0": { "order": 0, "parts": { ... } } } }`,
  one `parts` entry per panel below. Every part MUST carry:
  - a `metadata.inputs` block scoping it to the correct source resource ID
    (Application Insights, the Workbook, or the Resource Group), and
  - a `metadata.settings.content.options.chart.title` (or equivalent) string
    naming what the panel shows and its time window, per FR-010.
- **Auto-refresh**: The dashboard's `metadata.model.timeRange` /
  refresh-interval setting is 5 minutes, applying to the Failure,
  Performance, and User Statistic parts (FR-012). The Cost part is not
  bound by this interval (see research.md §4).
- **Replace semantics**: `terraform apply` sets the entire
  `dashboard_properties` document — there is no partial/merge update path,
  so every apply fully replaces the prior panel layout (no orphaned panels).

## Panel query contracts

| Panel | Part type | Source | Query / metric |
|---|---|---|---|
| Failed requests | `MonitorChartPart` | App Insights | `requests/failed` |
| Exceptions | `MonitorChartPart` | App Insights | `exceptions/count` |
| Response time / throughput | `MonitorChartPart` | App Insights | `requests/duration`, `requests/count` |
| Top slow/failing dependencies | `LogsDashboardPart` (KQL) | App Insights Log Analytics | `dependencies \| summarize ... \| top N by duration desc` (+ failure variant), with a link to Transaction Search |
| User statistics | `LogsDashboardPart` (KQL) | App Insights Log Analytics | `customEvents`/`pageViews \| summarize distinct users/sessions by bin(timestamp, ...)` |
| Resource group cost | `WorkbookPinnedPart` | Azure Cost Management via Workbook | `ActualCost` query scoped to the `llm-dungeon` Resource Group ID, no grouping dimension |

Exact KQL text and metric namespaces are an implementation detail of the
Terraform JSON (`dashboard.tf`), not a contract consumed by another system —
this table is the interface boundary: which data source and query *shape*
each panel is contractually bound to, so a future change to one panel's
exact query doesn't silently drift from what the panel claims to show.

## Access contract (FR-011)

No new identity/permission surface is introduced. Anyone holding an Azure
RBAC role (Reader, Monitoring Reader, Contributor, or Owner) on the
`llm-dungeon` Resource Group can open this dashboard, because it is an
ordinary resource inside that group — this is the existing Azure RBAC
contract, not a dashboard-specific one.

## Deployment contract (FR-008, FR-009)

The dashboard ships through the existing Terraform + GitHub Actions contract
already documented in `docs/INFRASTRUCTURE.md` and
`specs/007-azure-infrastructure-provisioning/contracts/`:
`terraform-validate.yml` on PR, `infrastructure-deploy.yml` (manual,
approval-gated) to apply. No new workflow or contract is added.
