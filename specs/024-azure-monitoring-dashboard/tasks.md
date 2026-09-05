---

description: "Task list for Azure Observability & Cost Dashboard"
---

# Tasks: Azure Observability & Cost Dashboard

**Input**: Design documents from `/specs/024-azure-monitoring-dashboard/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/dashboard-contract.md, quickstart.md

**Tests**: A post-apply resource-existence test is included — it is explicitly
designed in plan.md's Project Structure and Constitution Check (Principle I),
not optional boilerplate. Panel-level *data* correctness is intentionally not
automated (research.md §7) and is instead covered by quickstart.md's manual
validation.

**Organization**: This is an infrastructure-only feature — a single Terraform
file (`dashboard.tf`) whose `dashboard_properties` JSON document is built up
incrementally, one `parts` entry per user story, in priority order. Because
almost every task edits the same JSON document in the same file, most tasks
are **sequential** (not `[P]`) even though they map to independent user
stories — parallelizing edits to one JSON document across contributors would
cause merge conflicts, not independent delivery. Each user story phase is
still independently *verifiable*: once its parts are added, `terraform plan`
and quickstart.md's per-story validation confirm that story's panels work
before moving to the next.

## Path Conventions

Infrastructure-only change (per plan.md's Project Structure) — all paths are
under `infrastructure/`:

- `infrastructure/terraform/dashboard.tf` — new file, the dashboard + cost
  workbook resources
- `infrastructure/terraform/locals.tf`, `outputs.tf` — existing files, small
  additions
- `infrastructure/tests/test_dashboard.py` — new post-apply test file
- `infrastructure/tests/requirements.txt` — existing file, one addition

---

## Phase 1: Setup

**Purpose**: Establish the new Terraform file and naming so later phases only
add to an already-valid, already-`fmt`-clean resource.

- [ ] T001 Add `dashboard_name = "${local.name_prefix}dash${local.name_suffix}"` to the `locals` block in `infrastructure/terraform/locals.tf`, following the existing naming convention documented at the top of that file (data-model.md's Dashboard Definition entity).
- [ ] T002 Create `infrastructure/terraform/dashboard.tf` with a header comment (matching `monitoring.tf`'s style) referencing data-model.md's Dashboard Definition and Resource Group Cost Estimate entities, and a placeholder `azurerm_portal_dashboard` resource block (`name = local.dashboard_name`, `resource_group_name`/`location` from `data.azurerm_resource_group.rg`, `tags = local.common_tags`) with an empty `dashboard_properties` JSON (`{"lenses":{}}`) so the file is syntactically valid before panels are added.
- [ ] T003 Run `terraform fmt` and `terraform validate` in `infrastructure/terraform/` to confirm the new file is syntactically valid before building out `dashboard_properties`.

**Checkpoint**: `dashboard.tf` exists, named correctly, and validates — ready for the JSON body to be built out phase by phase.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared `dashboard_properties` document structure (lens/order, 5-minute auto-refresh, shared time-range input) that every panel in every subsequent user story phase plugs into. No panel content is added yet.

**⚠️ CRITICAL**: All user story phases append `parts` entries into the `lenses.0.parts` map this phase creates — this must be correct first.

- [ ] T004 In `infrastructure/terraform/dashboard.tf`, replace the placeholder `dashboard_properties` with the real `jsonencode({ lenses = { "0" = { order = 0, parts = {} } } })` skeleton (contract: dashboard-contract.md's "`dashboard_properties` shape"), using a Terraform local (e.g. `local.dashboard_parts`) merged in so each later phase adds to that map rather than editing one giant literal.
- [ ] T005 In `infrastructure/terraform/dashboard.tf`, add the dashboard's top-level `metadata.model.timeRange` and auto-refresh-interval settings (5 minutes) to the `dashboard_properties` document per FR-012 and contracts/dashboard-contract.md's "Auto-refresh" clause, scoped so it applies to the Failure/Performance/User-Statistics parts added in Phases 3-5.
- [ ] T006 Add `output "dashboard_id"` (value `azurerm_portal_dashboard.dashboard.id`) and `output "dashboard_name"` (value `azurerm_portal_dashboard.dashboard.name`) to `infrastructure/terraform/outputs.tf`, following the existing output style, for use by the post-apply test in Phase 6.
- [ ] T007 Run `terraform fmt` and `terraform validate` in `infrastructure/terraform/` to confirm the skeleton `dashboard_properties` document is well-formed.

**Checkpoint**: Foundation ready — every user story phase below only needs to add entries into `local.dashboard_parts`.

---

## Phase 3: User Story 1 - See Application Failures at a Glance (Priority: P1) 🎯 MVP

**Goal**: A dashboard panel set showing failed request counts, exception counts/types, and error trends over a recent time window (FR-002), each panel labeled with what it shows and its window (FR-010).

**Independent Test**: Deploy with only this phase's parts present; open the dashboard and confirm failed-request and exception counts/trends are visible and match Application Insights' own Failures blade for the same window (including a clear zero/healthy state when there are no failures — quickstart.md "Validate (User Story 1)").

### Implementation for User Story 1

- [ ] T008 [US1] In `infrastructure/terraform/dashboard.tf`, add a `MonitorChartPart` entry to `local.dashboard_parts` for the `requests/failed` metric on `azurerm_application_insights.appinsights` (contracts/dashboard-contract.md's Panel query contract table), with a `metadata.settings.content.options.chart.title` naming the panel and its time window (FR-010, default last 24h).
- [ ] T009 [US1] In `infrastructure/terraform/dashboard.tf`, add a `MonitorChartPart` entry for the `exceptions/count` metric on the same Application Insights resource, with title/window metadata per FR-010.
- [ ] T010 [US1] Run `terraform fmt` and `terraform validate` in `infrastructure/terraform/`, then `terraform plan` to confirm only the expected `azurerm_portal_dashboard.dashboard` change appears.

**Checkpoint**: User Story 1 is fully functional and independently deployable/testable — failures are visible without any other panel existing yet.

---

## Phase 4: User Story 2 - Understand Performance and Request Traces (Priority: P2)

**Goal**: Response time/latency, throughput, and a top-N slowest/failing dependency summary with a link to full trace details (FR-003, FR-004).

**Independent Test**: With Phase 3 + this phase's parts present, confirm response time/throughput panels match the App Insights Performance blade, and the top-N dependency panel lists entries (or an explicit no-data state) whose links open the corresponding Application Insights trace detail (quickstart.md "Validate (User Story 2)").

### Implementation for User Story 2

- [ ] T011 [US2] In `infrastructure/terraform/dashboard.tf`, add `MonitorChartPart` entries to `local.dashboard_parts` for `requests/duration` (avg + percentiles) and `requests/count` (throughput) on `azurerm_application_insights.appinsights`, titled/windowed per FR-010.
- [ ] T012 [US2] In `infrastructure/terraform/dashboard.tf`, add a `LogsDashboardPart` entry running a KQL query against the `dependencies` table (via `azurerm_log_analytics_workspace.logs`) that summarizes the top N slowest and failing dependencies over the panel's window (`summarize ... | top N by duration desc`, plus a failure-rate variant), rendered as a table, per data-model.md's Trace/Dependency Record entity and contracts/dashboard-contract.md's query-shape contract.
- [ ] T013 [US2] In the same `LogsDashboardPart` from T012, add the "open in Application Insights" link/markdown pointing at the App Insights resource's Transaction Search blade, satisfying FR-004's "link to the corresponding Application Insights trace details" requirement.
- [ ] T014 [US2] Run `terraform fmt` and `terraform validate` in `infrastructure/terraform/`, then `terraform plan` to confirm the expected incremental change to `azurerm_portal_dashboard.dashboard`.

**Checkpoint**: User Stories 1 AND 2 both work independently — failures and performance/traces are both visible.

---

## Phase 5: User Story 3 - Review User Statistics (Priority: P3)

**Goal**: Active user/session activity count and trend over a recent time window (FR-005).

**Independent Test**: With Phases 3-4 + this phase's part present, confirm the user/session activity panel shows a count and trend consistent with the application's own custom telemetry for the same window (quickstart.md "Validate (User Story 3)").

### Implementation for User Story 3

- [ ] T015 [US3] In `infrastructure/terraform/dashboard.tf`, add a `LogsDashboardPart` entry to `local.dashboard_parts` running a KQL query against `customEvents`/`pageViews` (via `azurerm_log_analytics_workspace.logs`) that summarizes distinct users/sessions bucketed over time, per data-model.md's User Statistic entity, titled/windowed per FR-010, subject to the 5-minute refresh from T005 (FR-012).
- [ ] T016 [US3] Run `terraform fmt` and `terraform validate` in `infrastructure/terraform/`, then `terraform plan` to confirm the expected incremental change.

**Checkpoint**: User Stories 1, 2, AND 3 all work independently.

---

## Phase 6: User Story 4 - See Estimated Resource Group Cost (Priority: P4)

**Goal**: A single aggregate estimated cost figure for the `llm-dungeon` Resource Group, labeled with the covered billing period and marked as an estimate (FR-006).

**Independent Test**: With all prior phases + this phase's workbook/part present, confirm the cost panel shows one aggregate figure labeled with its billing period and "estimate" wording, cross-checked within ±10% of Azure Cost Management's own Resource-Group-scoped cost for the same period (quickstart.md "Validate (User Story 4)", SC-005).

### Implementation for User Story 4

- [ ] T017 [US4] In `infrastructure/terraform/dashboard.tf`, define the Azure Monitor Workbook resource (`azurerm_application_insights_workbook`, or the minimal equivalent supported by the pinned `azurerm` provider version) scoped to `data.azurerm_resource_group.rg`, named per the `local.name_prefix`/`local.name_suffix` convention, containing a Cost Management `ActualCost` query (`microsoft.costmanagement/query`) scoped to the Resource Group ID with no grouping dimension (research.md §4, data-model.md's Resource Group Cost Estimate entity).
- [ ] T018 [US4] In the Workbook's query/markdown content from T017, include text stating the billing period the figure covers and that it is an estimate, satisfying the Edge Case in spec.md ("incomplete/delayed cost data... labeled as an estimate").
- [ ] T019 [US4] In `infrastructure/terraform/dashboard.tf`, add a `WorkbookPinnedPart` entry to `local.dashboard_parts` referencing the Workbook from T017, per contracts/dashboard-contract.md's Panel query contract table (this part is not subject to the 5-minute refresh from T005 per research.md §4).
- [ ] T020 [US4] Run `terraform fmt` and `terraform validate` in `infrastructure/terraform/`, then `terraform plan` to confirm the expected final incremental change (new Workbook resource + updated `azurerm_portal_dashboard.dashboard`).

**Checkpoint**: All four user stories are independently functional — the dashboard now matches spec.md's full FR-001 through FR-006 scope.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Automated verification, documentation, and end-to-end validation across all four stories together.

- [ ] T021 [P] Add `azure-mgmt-resource` to `infrastructure/tests/requirements.txt` (needed to look up the generic `Microsoft.Portal/dashboards` resource by ID in T022, since no dedicated dashboard-specific SDK client exists).
- [ ] T022 Create `infrastructure/tests/test_dashboard.py`, following the fixture pattern in `test_resource_creation.py`/`conftest.py`: a `resource_client` fixture (`azure.mgmt.resource.ResourceManagementClient`) and a test asserting the dashboard resource at `terraform_outputs["dashboard_id"]` exists with `name == terraform_outputs["dashboard_name"]` (plan.md's Constitution Check, Principle I).
- [ ] T023 Add a short "Observability & Cost Dashboard" subsection to `docs/INFRASTRUCTURE.md` (near the existing Application Insights/monitoring description) documenting: the dashboard is defined in `dashboard.tf`, deploys via the existing `terraform-validate.yml`/`infrastructure-deploy.yml` pipeline (FR-008/FR-009), and is opened via Azure Portal → the `llm-dungeon` Resource Group by anyone already holding a Reader/Monitoring Reader/Contributor/Owner RBAC role on that group (FR-011, research.md §5 — no new access-list resource).
- [ ] T024 Run the full `infrastructure/tests/test_terraform_validate.sh` suite locally to confirm `terraform fmt -check` and `terraform validate` both pass on the completed `dashboard.tf`.
- [ ] T025 Execute quickstart.md's Deploy steps (merge, trigger `infrastructure-deploy.yml`, approve `production-infra`) and all four "Validate (User Story N)" sections plus the "Validate (auto-refresh)" and "Validate (redeploy replaces layout)" sections end-to-end against the live `llm-dungeon` dashboard.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — creates `dashboard.tf` and its naming.
- **Foundational (Phase 2)**: Depends on Phase 1 — establishes the shared JSON skeleton and refresh setting that every user story phase appends into. BLOCKS all user story phases.
- **User Stories (Phases 3-6)**: Each depends on Phase 2. They are functionally independent (each adds its own `parts` entries and can be deployed/validated on its own per quickstart.md), but because all phases edit the same `local.dashboard_parts` map in the same file, they are executed **sequentially in priority order** (P1 → P2 → P3 → P4) to avoid merge conflicts on the same JSON structure.
- **Polish (Phase 7)**: Depends on Phases 3-6 all being complete (the test and quickstart validation exercise the fully-assembled dashboard).

### Within Each User Story Phase

- Panel/part definitions before the `terraform fmt`/`validate`/`plan` confirmation task.
- Phase 4's link addition (T013) depends on the `LogsDashboardPart` it augments (T012).
- Phase 6's pinned part (T019) depends on the Workbook resource existing first (T017, T018).

### Parallel Opportunities

- Within Phase 7, T021 (requirements.txt) can run in parallel with T023 (docs) — both are `[P]`, independent files. T022 depends on T021 (needs the new dependency installed/declared first); T024/T025 depend on all prior phases.
- Because every other task in Phases 1-6 edits the same `dashboard.tf` file, there are no further `[P]` opportunities in those phases — this is expected for a single-resource JSON-document feature, not an oversight.

---

## Parallel Example: Phase 7

```bash
# These two can run together — different files, no shared state:
Task: "Add azure-mgmt-resource to infrastructure/tests/requirements.txt"
Task: "Add Observability & Cost Dashboard subsection to docs/INFRASTRUCTURE.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks all user stories)
3. Complete Phase 3: User Story 1 (Failures)
4. **STOP and VALIDATE**: `terraform plan`/`apply` this state alone, open the dashboard, confirm failure panels work per quickstart.md's User Story 1 section
5. Deploy/demo if ready — this alone already satisfies FR-002, FR-007, FR-008-FR-010, FR-012 (partially) for the failure panels

### Incremental Delivery

1. Setup + Foundational → dashboard skeleton exists, validates, deploys empty
2. Add User Story 1 → validate independently → deploy/demo (MVP!)
3. Add User Story 2 → validate independently → deploy/demo
4. Add User Story 3 → validate independently → deploy/demo
5. Add User Story 4 → validate independently → deploy/demo (full FR-001–FR-012 scope)
6. Phase 7 polish (test, docs, full quickstart pass) once all four stories are in

---

## Notes

- This feature has no `src/frontend` or `src/backend` changes — every task path is under `infrastructure/`.
- No contract/integration test tasks are generated per user story because there is no API surface (contracts/dashboard-contract.md: "the JSON contract Terraform submits... There is no API surface, CLI, or library contract to define"); the one test task (T022) is a post-apply infrastructure resource-existence check, per plan.md's explicit test design.
- Panel *data* correctness (do the KQL queries return sane numbers) is deliberately left to quickstart.md's manual validation (T025), not automated — consistent with research.md §7 and Constitution Principle IX.
- Commit after each task or logical group; stop at any phase checkpoint to validate that story's panels independently before continuing.
