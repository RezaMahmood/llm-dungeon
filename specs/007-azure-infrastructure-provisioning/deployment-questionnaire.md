# Deployment Configuration Questionnaire

**Status**: Answered 2026-08-29 (interactive chat session) and folded back into `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/*.md`. Kept here as a record of the decisions and their rationale.

---

## 1. Identity & Subscription

| Item | Value |
|---|---|
| Azure Subscription ID | Not needed in the docs — supplied at deploy time via the `production` GitHub environment's `AZURE_SUBSCRIPTION_ID` variable, never hardcoded |
| Azure Tenant ID | Same — via `AZURE_TENANT_ID` GitHub environment variable |
| Subscription access confirmed for the account that will run bootstrap (`az login`)? | Confirm before first bootstrap run (operational step, not a docs change) |

## 2. Region

| Item | Value |
|---|---|
| Primary Azure region | **West Europe** (`westeurope`) — applied everywhere; fixed the `eastus`/`uksouth` inconsistency |
| Static Web App / AI Foundry region compatibility | West Europe supports both; no conflict |
| Data-residency requirement | EU residency — satisfied by West Europe |

## 3. Naming Convention & Tags

| Item | Value |
|---|---|
| Resource name prefix | **`llmdungeon`** (hyphen-free) — replaced `myownchat` everywhere |
| Naming pattern | `{prefix}-{resource-type}-{environment}` for most resources (e.g. `llmdungeon-func-prod`); **hyphen-free** `{prefix}{resource-type}{environment}` for Storage Accounts specifically (e.g. `llmdungeonassetsprod`) — documented as an explicit exception in data-model.md |
| Tags on every resource | `managed_by=terraform`, `project=llm-dungeon`, `application=llm-dungeon`, `environment=production`, `owner=<team/person>` (owner value still needs a real name/team filled in before first apply — see Open Items) |

## 4. Networking

| Item | Value |
|---|---|
| VNet | **Terraform creates a new VNet** (`llmdungeon-vnet-prod`) inside `llm-dungeon`, not pre-existing |
| VNet address space | `10.0.0.0/16` |
| Functions VNet-integration subnet | `10.0.1.0/24` |
| Private-endpoints subnet | `10.0.2.0/24` |
| Functions hosting plan | **Flex Consumption** — natively supports VNet integration, pay-per-execution, no reserved capacity |

## 5. Compute & Data Tiers

| Item | Value |
|---|---|
| Cosmos DB consistency level | **Session** |
| Cosmos DB backup policy | **Periodic** (Azure defaults: every 4h, 7-day retention) |
| Storage account replication | **LRS** |
| Static Web App SKU | **Standard** |

## 6. Azure AI Foundry / OpenAI Model

| Item | Value |
|---|---|
| Model | **gpt-4o-mini** |
| Deployment capacity | **1,000 TPM (1K TPM)** — Terraform `capacity = 1` (fixed the "1 TPM" typo) |
| Content filtering | Azure default — not customized |

## 7. Observability & Cost

| Item | Value |
|---|---|
| Log Analytics Workspace | **Created** (`llmdungeon-logs-prod`), `PerGB2018` SKU, 30-day retention, backs workspace-based Application Insights |
| Application Insights retention/quota | 30 days retention, 5 GB/day ingestion cap (unchanged defaults) |
| Budget / cost alert | **Yes** — `$50/month` on the `llm-dungeon` Resource Group, email alert at 80% and 100% |
| Failure alerting (Functions errors, connectivity, OIDC) | Not yet decided — see Open Items |

## 8. GitHub / CI-CD

| Item | Value |
|---|---|
| GitHub org/repo | **`RezaMahmood/llm-dungeon`** — corrected everywhere (was `RezaMahmood/myownchat`) |
| Deployment branch | **`main`** only |
| GitHub environment | **`production`** |
| Required reviewers / manual approval gate | **Yes** — required reviewer configured on the `production` environment; `terraform-apply.yml` and both deploy workflows pause for approval |

## 9. Security Baseline

| Item | Value |
|---|---|
| Minimum TLS version | **TLS 1.2** on Storage, Cosmos DB, and Functions |
| GitHub OIDC Managed Identity role scope | **Contributor on the `llm-dungeon` Resource Group** (kept as originally planned) |

---

## Open Items (not yet answered — small enough to leave for implementation time)

- **`owner` tag value**: needs a real team/person name before first `terraform apply` (currently `"TBD"` placeholder in `contracts/terraform-contract.md`)
- **Failure alerting**: no action group / notification channel (email, Teams, webhook) chosen yet for Functions errors, private-endpoint connectivity failures, or OIDC auth failures — infra can ship without this, add later
- **`budget_alert_email`**: the email address to receive the $50/month budget notifications needs a real value before first apply

---

## Issues Found (fixed while folding these answers back in)

1. ~~Region inconsistency (`eastus` vs `uksouth`)~~ — fixed, all `westeurope` now
2. ~~`myownchat` vs `llm-dungeon` naming mismatch~~ — fixed, `llmdungeon` prefix and `RezaMahmood/llm-dungeon` repo everywhere
3. ~~Storage account name typo (`myowchatstage`)~~ — fixed, consistently `llmdungeontstateprod`
4. ~~Storage account naming pattern contradiction~~ — fixed, hyphen-free pattern now explicitly documented as an exception
5. ~~VNet referenced but never defined~~ — fixed, new **Virtual Network** entity added to data-model.md/research.md/plan.md/terraform-contract.md
6. ~~`plan.md`'s stale `NEEDS CLARIFICATION` markers~~ — fixed, Technical Context now reflects research.md's resolutions
7. ~~AI Foundry capacity typo ("1 TPM")~~ — fixed, now 1,000 TPM / capacity unit `1`
8. ~~Log Analytics Workspace missing~~ — fixed, new entity added, Application Insights now explicitly workspace-based
