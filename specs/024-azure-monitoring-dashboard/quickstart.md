# Quickstart: Azure Observability & Cost Dashboard

Validates that the dashboard deploys via the existing Terraform/GitHub
Actions pipeline and that every panel from `spec.md`'s user stories renders
correctly end to end.

## Prerequisites

- `llm-dungeon` Resource Group already provisioned (007-azure-infrastructure-provisioning).
- Azure RBAC role (Reader, Monitoring Reader, Contributor, or Owner) on the
  `llm-dungeon` Resource Group for the account used to validate (FR-011 —
  no separate grant needed, see `research.md` §5).
- Local `terraform` CLI matching `infrastructure/terraform/versions.tf`, or
  access to trigger `infrastructure-deploy.yml` via `workflow_dispatch`.

## Deploy

1. Merge the PR containing `infrastructure/terraform/dashboard.tf` to `main`
   (goes through `terraform-validate.yml` at PR time).
2. Manually trigger `infrastructure-deploy.yml` (`workflow_dispatch`) and
   approve the `production-infra` environment gate when prompted. Confirm
   the `plan` step shows one new/changed resource:
   `azurerm_portal_dashboard.dashboard` (and its Workbook, if a separate
   resource).
3. Confirm `apply` completes successfully.

## Validate (User Story 1 — Failures)

1. Open the Azure Portal → `llm-dungeon` Resource Group → the dashboard.
2. Confirm the Failed Requests and Exceptions panels are visible and each
   panel's title states what it shows and its time window (FR-010).
3. If the application has had recent failures, confirm the counts/trend are
   non-zero and match the same window in Application Insights' own Failures
   blade. If it has had zero failures, confirm the panel shows a clear
   zero/healthy state, not an empty or broken-looking chart.

## Validate (User Story 2 — Performance & Traces)

1. Confirm the response time/latency and throughput panels show data
   consistent with the App Insights Performance blade for the same window.
2. Confirm the top-N slow/failing dependencies panel lists entries (or an
   explicit no-data state if none exist in the window) and that each row's
   link opens the corresponding Application Insights trace/transaction
   detail.

## Validate (User Story 3 — User Statistics)

1. Confirm the user/session activity panel shows a count and trend
   consistent with the application's own custom telemetry for the same
   window.

## Validate (User Story 4 — Cost)

1. Confirm the cost panel shows a single aggregate figure for the
   `llm-dungeon` Resource Group, labeled with the billing period it covers
   and marked as an estimate.
2. Cross-check against Azure Cost Management's own Resource-Group-scoped
   cost analysis for the same period; confirm the two are within ±10%
   (SC-005) — allow for Cost Management's own reporting delay.

## Validate (auto-refresh — FR-012)

1. Leave the dashboard open for at least 5 minutes without reloading.
2. Confirm the Failure, Performance, and User Statistic panels update on
   their own (a new data point moves the trend, or a changed count) without
   a manual page reload. The Cost panel is not required to auto-refresh on
   this interval (research.md §4).

## Validate (redeploy replaces layout — Edge Case)

1. Make a small change to a panel in `dashboard.tf` (e.g. reorder two
   parts), open a PR, merge, and re-run `infrastructure-deploy.yml`.
2. Confirm the live dashboard reflects only the new layout — no leftover or
   duplicate panels from the previous version (SC-004).
