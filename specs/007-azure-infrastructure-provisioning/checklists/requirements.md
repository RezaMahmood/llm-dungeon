# Specification Quality Checklist: Azure Infrastructure Provisioning

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-28
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details beyond what the feature itself specifies (this is an
      infrastructure feature; the named Azure services and Terraform/GitHub Actions
      tooling are the requirement, not an implementation detail to abstract away)
- [x] Focused on engineering/operational value and business needs (reproducibility,
      security, low operational overhead)
- [x] Written to be understandable by a technical stakeholder reviewing infrastructure
      decisions (the audience for this spec is inherently technical)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic in their outcome framing (measure private
      connectivity, keyless auth, and OIDC usage as outcomes, not code-level detail)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No extraneous implementation detail beyond what the feature itself requires

## Notes

- All items pass. The 3 clarifications were resolved directly by the user:
  single Production environment only (FR-013), public HTTPS for the Static Web
  App-to-Function App path as a documented exception (FR-014), and Azure AI Foundry
  provisioning with a deployed model, Managed Identity, and private link included in
  scope (FR-015, plus extended FR-007/FR-008).
- 2026-08-29: Updated to require the GitHub OIDC federated credential be anchored to a
  dedicated user-assigned Managed Identity rather than a traditional Entra App
  Registration/service principal (FR-011a, User Story 3, SC-004). All items re-checked
  and still pass; no new [NEEDS CLARIFICATION] markers introduced.
- 2026-08-29: Updated plan/data-model/research/contracts/quickstart to provision all
  Azure resources into a single, pre-existing Resource Group (`llm-dungeon`) referenced
  via a Terraform data source rather than created by Terraform; added a matching
  Assumption to spec.md. All items re-checked and still pass; no new
  [NEEDS CLARIFICATION] markers introduced.
- 2026-08-29: Answered the deployment-questionnaire.md decisions (region=westeurope,
  naming prefix=llmdungeon, new Terraform-managed VNet, Functions on Flex Consumption,
  Cosmos Session/Periodic-backup, Storage LRS, AI Foundry gpt-4o-mini @ 1K TPM, SWA
  Standard, Log Analytics Workspace + workspace-based App Insights, $50/mo budget
  alert, required-reviewer approval gate on the production GitHub environment, TLS 1.2
  minimum, extended tag set) and folded them into plan/research/data-model/contracts/
  quickstart; also fixed the 8 inconsistencies logged in deployment-questionnaire.md's
  "Issues Found" (region mismatch, myownchat/llm-dungeon naming, storage-account typo
  and invalid naming pattern, undefined VNet, stale NEEDS CLARIFICATION markers in
  plan.md, AI Foundry capacity typo, missing Log Analytics Workspace). All items
  re-checked and still pass; no new [NEEDS CLARIFICATION] markers introduced. Two
  small values remain open for implementation time (owner tag, budget alert email —
  see deployment-questionnaire.md's Open Items).
- 2026-08-29: Ran `/speckit-analyze` against spec.md/plan.md/tasks.md and resolved its
  findings: reworded FR-002 (was unsatisfiable — said "Terraform MUST provision" its own
  backend storage, contradicting the bootstrap-script design); split the GitHub
  environment in two (`production` for app deploys, `production-infra` for Terraform
  apply only) so the required-reviewer approval gate no longer contradicts FR-010/SC-006's
  "no manual deployment step" for routine deploys; resolved the `owner`/`budget_alert_email`
  `"TBD"` placeholders to real values; expanded T030 to also test the OIDC failure path
  (FR-016) and added a drift-detection check to quickstart.md Scenario 2 (FR-016, Edge
  Cases); added the GitHub CLI to plan.md's dependencies. All items re-checked and still
  pass; no new [NEEDS CLARIFICATION] markers introduced; no Open Items remain except
  failure-alerting routing, deferred by choice.
- 2026-08-29: Re-ran `/speckit-analyze` and fixed the two findings it surfaced: inserted
  a new Foundational task T014 (creates the `production`/`production-infra` GitHub
  environments and the `production-infra` required-reviewer rule) so the approval gate
  is active before `terraform-apply.yml` (T024) first runs, instead of depending on a
  later User Story 5 task — this required renumbering T014 onward through T044; and wired
  `terraform-validate.yml` (T013) to actually invoke `test_terraform_validate.sh` (T012)
  instead of duplicating its logic inline. Tasks.md now has 44 tasks (T001-T044), all
  IDs sequential and referenced consistently. No CRITICAL/HIGH findings remain.
- 2026-08-29: Ran `/speckit-implement`. All 44 tasks except the six "execute
  quickstart end-to-end" ones (T027, T030, T032, T037, T040, T044) are complete:
  every `terraform/*.tf` file, all 5 GitHub Actions workflows, `scripts/bootstrap.sh`,
  `scripts/configure-github-environment.sh`, and all 4 `tests/infrastructure/*`
  suites are written and pass `terraform fmt`/`validate` against the real azurerm
  v5.3.0 provider (contract said `>= 3.80.0`, no upper bound — v5 has breaking
  changes from v3/v4, e.g. `azurerm_function_app_flex_consumption` for the Flex
  Consumption Function App, `azurerm_cosmosdb_sql_role_assignment` for Cosmos
  data-plane RBAC, `private_endpoint_network_policies` as a string not a bool).
  Live provisioning against the real `llm-dungeon` subscription (westeurope):
  the `production`/`production-infra` GitHub environments were created (T014,
  confirmed: `production` unprotected, `production-infra` requires reviewer
  RezaMahmood, both branch-restricted to `main`); `scripts/bootstrap.sh` ran
  successfully (Terraform state Storage Account, GitHub OIDC Managed Identity
  with federated credential and Contributor role); `terraform apply` provisioned
  21 of 31 resources (VNet, both subnets, all 3 Private DNS zones + VNet links,
  Storage/OpenAI private endpoints, Storage Account + both containers, AI
  Foundry account + `gpt-4o-mini` deployment, Service Plan, Static Web App, Log
  Analytics, Application Insights, budget alert).
  Two implementation-time corrections made along the way (docs updated to
  match): (1) the Terraform state Storage Account's `default_action` was
  changed from `Deny` to `Allow` — as originally specified it blocked every
  caller (GitHub-hosted runners included), since it's created before any VNet
  exists; access is still Azure-AD-gated via `use_azuread_auth`, never
  anonymous/key-based. (2) `azurerm_cognitive_deployment`'s `sku.name` for
  `gpt-4o-mini` changed from `Standard` (no longer offered in `westeurope`) to
  `DataZoneStandard`, chosen over `GlobalStandard` to keep inference within the
  EU data zone per the EU-residency requirement.
  **Blocked, not resolved**: Cosmos DB creation (`llmdungeon-cosmos-prod`) fails
  with Azure's `ServiceUnavailable`/"high demand ... zonal redundant ...
  cannot fulfill your request at this time" in `westeurope` — confirmed via a
  direct `az cosmosdb create` probe (different account name, bypassing
  Terraform) that this is Azure's own regional capacity, not a config issue.
  Cosmos DB and everything reading its outputs (the SQL database/container,
  its Cosmos data-plane role assignment, and the Function App itself — its
  `app_settings` include `COSMOS_ENDPOINT`) remain unprovisioned. The user
  chose to stop and resume later rather than keep retrying automatically.
  **To resume**: re-run `terraform apply -var-file=terraform.tfvars` from
  `terraform/` (with `TF_VAR_azure_subscription_id`/`TF_VAR_azure_tenant_id`
  set, or via `terraform-apply.yml` once this branch merges to `main`) — the
  21 already-applied resources will show no changes; only the 10 blocked ones
  will be attempted. If Cosmos DB creation leaves a `provisioningState: Failed`
  leftover again, delete it (`az cosmosdb delete --name llmdungeon-cosmos-prod
  --resource-group llm-dungeon --yes`) before retrying — Azure won't let
  Terraform recreate over a failed record with the same name.
  T027/T030/T032/T037/T040/T044 (the quickstart end-to-end validations) are
  correctly left unchecked in tasks.md pending Cosmos DB/Functions completion.
- 2026-08-29: Resolved the Cosmos DB block. Probed `uksouth` directly via `az
  cosmosdb create` (bypassing Terraform) and confirmed capacity there; added a
  dedicated `cosmos_region` variable (default `uksouth`) used only by
  `azurerm_cosmosdb_account.cosmos`, independent of `azure_region`
  (`westeurope`, unchanged for every other resource) — Private Link works
  cross-region so the VNet/subnets/private endpoint stay in West Europe. Made
  single-region/no-redundancy explicit: `automatic_failover_enabled = false`,
  `multiple_write_locations_enabled = false`, `zone_redundant = false`. The
  user confirmed there is no data-residency requirement — region choice is
  proximity-to-user only — so `research.md`/`data-model.md`/both contracts/
  `deployment-questionnaire.md` were updated to drop the "EU residency"
  framing entirely rather than treat UK South as an exception needing
  justification. `terraform apply` then succeeded: **all 31 planned resources
  now exist** (`terraform state list` confirms 31 resources + the Resource
  Group data source). Ran the test suites against the live infrastructure:
  `test_resource_creation.py` (8/8 passed) and `test_private_connectivity.py`
  (6/6 passed after fixing two test-design bugs — the public-access-denied
  checks were hitting a bare Storage account root URL, which returns 400
  regardless of network rules, and Cognitive Services' shared unauthenticated
  "service operational" health page instead of a real data-plane operation;
  fixed to use `?comp=list` and `openai/models?api-version=...` respectively.
  `publicNetworkAccess: Disabled` was independently confirmed via `az cli` on
  both accounts throughout, so this was a test bug, not a misconfiguration).
  T027 marked complete. T030/T032/T037/T040/T044 remain unchecked — they
  require pushing to `main` to exercise the GitHub Actions-triggered
  deployment/OIDC/config-externalization workflows, which wasn't done this
  session (implementation stayed on the feature branch; merging to `main` is
  a separate decision for the user to make).
