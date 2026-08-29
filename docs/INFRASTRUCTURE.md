# Infrastructure Overview

Provisioned by [`007-azure-infrastructure-provisioning`](../specs/007-azure-infrastructure-provisioning/spec.md).
Full design detail lives in that feature's
[plan.md](../specs/007-azure-infrastructure-provisioning/plan.md),
[data-model.md](../specs/007-azure-infrastructure-provisioning/data-model.md),
and [contracts/](../specs/007-azure-infrastructure-provisioning/contracts/);
this page is a short map, not a restatement.

## Layout

- `terraform/` — all Azure resources, into the single pre-existing
  `llm-dungeon` Resource Group (West Europe). Split by concern:
  `main.tf` (Storage, Cosmos DB, AI Foundry, Functions, Static Web App),
  `network.tf` (VNet, subnets, private endpoints, Private DNS Zones),
  `monitoring.tf` (Log Analytics, Application Insights, budget alert),
  `identity.tf` (Functions Managed Identity role assignments).
- `.github/workflows/` — `terraform-validate.yml` (PR checks + drift-detecting
  plan), `terraform-apply.yml` (targets the `production-infra` environment,
  human-approval-gated), `backend-deploy.yml`/`frontend-deploy.yml` (target
  `production`, fully automatic), `infrastructure-tests.yml` (nightly +
  on-demand).
- `tests/infrastructure/` — Terraform validation wrapper plus pytest suites
  for resource existence, private connectivity, and OIDC authentication.
- `scripts/` — one-time `bootstrap.sh` (Terraform state storage + GitHub OIDC
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

## First-time setup and validation

Run through [quickstart.md](../specs/007-azure-infrastructure-provisioning/quickstart.md)
end-to-end — it covers bootstrap, `terraform apply`, GitHub Actions wiring,
private-connectivity verification, and the OIDC authentication check, in
that order.
