# Implementation Plan: Azure Observability & Cost Dashboard

**Branch**: `024-azure-monitoring-dashboard` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/024-azure-monitoring-dashboard/spec.md`

## Summary

Add a version-controlled Azure Dashboard (`Microsoft.Portal/dashboards`) to
`infrastructure/terraform/`, in the existing `llm-dungeon` Resource Group,
surfacing failures, performance, a top-N slow/failing dependency summary,
user statistics — all read from the existing Application Insights instance
via native Portal Monitor/Logs dashboard parts with a 5-minute auto-refresh —
plus a single aggregate resource-group cost estimate via a pinned Azure
Monitor Workbook querying Cost Management. No new compute, pipeline, or
access-control resource is introduced: the dashboard deploys through the
existing Terraform + `infrastructure-deploy.yml` pipeline, and is reachable
by anyone already holding an Azure RBAC role on the Resource Group.

## Technical Context

**Language/Version**: HCL (Terraform >= 1.5.0), `hashicorp/azurerm` provider >= 3.80.0 (both already pinned in `infrastructure/terraform/versions.tf`)

**Primary Dependencies**: `azurerm_portal_dashboard` (Microsoft.Portal/dashboards), an Azure Monitor Workbook resource for the cost panel, both reading from the existing `azurerm_application_insights.appinsights` / `azurerm_log_analytics_workspace.logs` and from Azure Cost Management — no new Terraform provider

**Storage**: N/A — this feature stores no application data; it defines a dashboard that reads existing telemetry and cost data

**Testing**: `infrastructure/tests/` pytest suite (post-apply resource-existence check, following the existing pattern in `test_resource_creation.py`) plus `infrastructure/tests/test_terraform_validate.sh` (plan-time `terraform validate`/fmt, already runs in `terraform-validate.yml`); panel-level data correctness validated manually via `quickstart.md` (Principle IX: non-blocking, post-ship)

**Target Platform**: Azure Portal (the dashboard is opened directly in the Azure Portal, not the application's own frontend)

**Project Type**: Infrastructure-only change (`infrastructure/terraform/`) — no `src/frontend` or `src/backend` changes

**Performance Goals**: N/A — no throughput/latency target for this feature itself; SC-001/SC-002 (time-to-diagnose) are UX outcomes of panel layout, not a system performance requirement

**Constraints**: Estimated cost panel MUST stay within ±10% of Azure's actual billed cost for the period (SC-005); failure/performance/user-statistics panels MUST auto-refresh every 5 minutes while open (FR-012); MUST NOT include an availability/uptime panel (FR-007)

**Scale/Scope**: One Resource Group (`llm-dungeon`), one dashboard resource, ~6 panels — no scale dimension beyond what already exists

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

- **Principle I (Meaningful, Automated Testing)**: Satisfied — a post-apply
  pytest check asserts the dashboard resource exists with expected
  configuration, following the existing `test_resource_creation.py` pattern;
  `terraform validate`/fmt already runs at PR time. Panel *data* correctness
  is not automatable without live telemetry (no coverage-inflation tests are
  added instead) and is covered by `quickstart.md`'s manual validation,
  consistent with Principle IX below. PASS.
- **Principle II (Secure-by-Default Access)**: N/A to this feature directly —
  it adds no user-facing page or API endpoint; it is a native Azure Portal
  resource, not part of the application. Access is governed by Azure RBAC
  (Security & Access Control Requirements), not Entra ID sign-in. PASS.
- **Principle III (Defined Technology Stack)**: No deviation — uses the
  already-adopted Terraform/`azurerm` stack; no new language, framework, or
  hosting model. PASS.
- **Principle IV (Simplicity Over Premature Scale)**: PASS — no new compute,
  polling service, or custom cost estimator; native dashboard parts and a
  Workbook read existing data directly (see research.md §2-4).
- **Principle V (Continuous Integration Gate)**: PASS — ships through the
  existing `terraform-validate.yml` PR gate; no bypass introduced.
- **Principle VI (Observability & AI Cost Transparency)**: N/A to add new
  telemetry — this feature *surfaces* existing OTel→App Insights telemetry
  rather than emitting new LLM call data. Does not weaken or replace the
  OTel/App Insights pairing. PASS.
- **Principle VII (Zero-Trust Azure Resource Communication)**: N/A — the
  dashboard resource itself is read by portal users via Azure RBAC, not by
  another Azure resource authenticating over the network; no Managed
  Identity/Private Endpoint applies to a Portal Dashboard resource. The
  Workbook's Cost Management query runs under the viewing user's own
  Azure AD context (standard Workbook behavior), not a stored credential.
  PASS.
- **Principle VIII / UI Design System & Accessibility**: N/A — this is a
  native Azure Portal resource, not a screen in this project's ReactJS
  frontend; the design-token layer, component classes, and screen contracts
  in `specs/designs/` govern the application's own UI, not Azure Portal
  chrome, which this feature does not touch or reimplement. No exception
  needed because no in-app UI is introduced.
- **Principle IX (Playtesting-Driven Quality)**: Panel-level manual
  validation (quickstart.md) is informational/non-blocking, consistent with
  this principle — CI's automated resource-existence check remains the
  actual merge gate. PASS.
- **Principle X (PII Protection by Design)**: N/A — dashboard panels surface
  aggregate metrics/cost, not individual user PII; no PII is written to the
  dashboard definition, commits, or PR content. PASS.
- **Principle XI (Implementer Design Latitude)**: N/A — no user-facing UI
  design sign-off gate applies to a Portal Dashboard's panel layout.
- **Principle XII (Right-Sized Scope)**: PASS — deliberately avoids adding a
  new access-list, role hierarchy, or dedicated pipeline (research.md §5-6);
  reuses existing RG-level RBAC and the existing infra deploy pipeline.
- **Principle XIII (AI Agent Division of Labor)**: Followed for this
  session's own git/PR workflow (branch, push, PR — not a design constraint
  on the dashboard itself).

No violations — Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/024-azure-monitoring-dashboard/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── dashboard-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
infrastructure/
├── terraform/
│   └── dashboard.tf          # NEW: azurerm_portal_dashboard + cost Workbook,
│                              #      wired to existing appinsights/log
│                              #      analytics resources in monitoring.tf
└── tests/
    └── test_dashboard.py      # NEW: post-apply resource-existence check,
                                #      alongside test_resource_creation.py
```

**Structure Decision**: Infrastructure-only change. No `src/frontend` or
`src/backend` directories are touched — this feature adds one new Terraform
file (`dashboard.tf`) to the existing `infrastructure/terraform/` layout
described in `docs/INFRASTRUCTURE.md`, plus one new test file in the existing
`infrastructure/tests/` suite. No new top-level directory, pipeline, or
project type is introduced.

## Complexity Tracking

*No violations — table not needed.*
