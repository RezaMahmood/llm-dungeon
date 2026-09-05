# Infrastructure Overview

Provisioned by [`007-azure-infrastructure-provisioning`](../specs/007-azure-infrastructure-provisioning/spec.md).
Full design detail lives in that feature's
[plan.md](../specs/007-azure-infrastructure-provisioning/plan.md),
[data-model.md](../specs/007-azure-infrastructure-provisioning/data-model.md),
and [contracts/](../specs/007-azure-infrastructure-provisioning/contracts/);
this page is a short map, not a restatement.

## Layout

- `infrastructure/terraform/` — all Azure resources, into the single pre-existing
  `llm-dungeon` Resource Group (West Europe). Split by concern:
  `main.tf` (Storage, Cosmos DB, AI Foundry, Functions, Static Web App),
  `network.tf` (VNet, subnets, private endpoints, Private DNS Zones),
  `monitoring.tf` (Log Analytics, Application Insights, budget alert),
  `dashboard.tf` (Portal Dashboard + cost estimate Workbook),
  `identity.tf` (Functions Managed Identity role assignments).
- `.github/workflows/` — `terraform-validate.yml` (PR checks + drift-detecting
  plan), `infrastructure-deploy.yml` (CD: manually triggered only, no
  version input; validates, tests, and plans fresh against the current
  state of `main` every run, then applies — targets the `production-infra`
  environment, human-approval-gated), `backend-deploy.yml`/`frontend-deploy.yml`
  (CD: manually triggered only, target `production`, no approval gate —
  these two also have an independently-versioned CI build step,
  infrastructure does not), `infrastructure-tests.yml` (nightly + on-demand).
  See `.github/workflows/README.md` for the full CI/CD split.
- `infrastructure/tests/` — Terraform validation wrapper plus pytest suites
  for resource existence, private connectivity, and OIDC authentication.
- `infrastructure/scripts/` — one-time `bootstrap.sh` (Terraform state storage + GitHub OIDC
  Managed Identity) and `configure-github-environment.sh` (populates
  repository variables from Terraform outputs).

## Architecture

```
GitHub Actions ──(federated OIDC, no stored secrets)──► GitHub OIDC Managed Identity
                                                                  │
                                                     terraform apply / az CLI
                                                                  ▼
                                          Resource Group "llm-dungeon" (pre-existing)
                                          ├─ VNet (10.0.0.0/16)
                                          │   ├─ Functions-integration subnet
                                          │   └─ Private-endpoints subnet ──► Storage / Cosmos DB / AI Foundry
                                          ├─ Azure Functions (Flex Consumption, system-assigned Managed Identity)
                                          ├─ Azure Static Web App
                                          ├─ Log Analytics Workspace + Application Insights
                                          └─ Consumption budget alert ($50/mo)
```

Functions reaches Storage, Cosmos DB, and AI Foundry exclusively over private
endpoints, authenticated via its own system-assigned Managed Identity — no
keys, connection strings, or stored credentials anywhere in this
configuration (Constitution Principle VII).

## Observability & Cost Dashboard

`dashboard.tf` (see
[`024-azure-monitoring-dashboard`](../specs/024-azure-monitoring-dashboard/spec.md))
defines a version-controlled Azure Portal Dashboard surfacing failures,
performance, a top-N slow/failing dependency summary, and user statistics —
all read live from the existing Application Insights / Log Analytics
resources above — plus a pinned Azure Monitor Workbook showing a single
aggregate estimated cost for the `llm-dungeon` Resource Group. It deploys
through the same `terraform-validate.yml` / `infrastructure-deploy.yml`
pipeline as every other resource here — no new pipeline. It is opened via
Azure Portal → the `llm-dungeon` Resource Group, by anyone already holding a
Reader, Monitoring Reader, Contributor, or Owner Azure RBAC role on that
group — no new access-list resource (FR-011, research.md §5).

## First-time setup and validation

Run through [quickstart.md](../specs/007-azure-infrastructure-provisioning/quickstart.md)
end-to-end — it covers bootstrap, `terraform apply`, GitHub Actions wiring,
private-connectivity verification, and the OIDC authentication check, in
that order.
