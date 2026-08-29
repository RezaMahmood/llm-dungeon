---

description: "Task list template for feature implementation"
---

# Tasks: Azure Infrastructure Provisioning

**Input**: Design documents from `/workspaces/llmdungeon/specs/007-azure-infrastructure-provisioning/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, deployment-questionnaire.md (all present)

**Tests**: Constitution Principle I (NON-NEGOTIABLE) requires automated tests for all functionality, and FR-016 requires an automated check per provisioned resource type and CI/CD pathway. Test tasks are therefore included, not optional.

**Organization**: Tasks are grouped by user story (from spec.md, priority order P1→P5) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Include exact file paths in descriptions

## Path Conventions

Infrastructure-as-code project. Terraform config at `terraform/` (repo root), CI/CD workflows at `.github/workflows/`, infrastructure tests at `tests/infrastructure/`, one-time operational scripts at `scripts/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding for the Terraform, CI, and test directories this feature adds.

- [X] T001 Create `terraform/`, `.github/workflows/`, `tests/infrastructure/`, and `scripts/` directories per plan.md's Project Structure
- [X] T002 [P] Create `terraform/versions.tf` pinning `required_version = ">= 1.5.0"` and the `azurerm` provider `>= 3.80.0` per research.md §1
- [X] T003 [P] Update `pytest.ini` so `testpaths` includes `tests/infrastructure` alongside the existing `backend/tests`
- [X] T004 [P] Create `tests/infrastructure/__init__.py` and `tests/infrastructure/conftest.py` with shared fixtures (Azure credential via `DefaultAzureCredential`, a Terraform-outputs loader that reads `terraform output -json`)
- [X] T005 [P] Create `terraform/locals.tf` with the naming-convention locals (`llmdungeon` prefix; hyphen-free variant for Storage Account names) and the common tags map (`managed_by`, `project`, `application`, `environment`, `owner`) per data-model.md's Terraform Configuration entity

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The backend, networking, and variable scaffolding every user story's Terraform resources build on top of.

**⚠️ CRITICAL**: No user story's Terraform resources can be applied until this phase is complete.

- [X] T006 [P] Create `scripts/bootstrap.sh` implementing contracts/deployment-config-contract.md's Bootstrap Procedure: verify the pre-existing `llm-dungeon` Resource Group exists (fail fast with a clear error if not — never create it), create the Terraform backend Storage Account + `terraform-state` container inside it, and create the GitHub OIDC Managed Identity with its federated credential (`az identity create` + `az identity federated-credential create`, not an App Registration) and a `Contributor` role assignment scoped to the `llm-dungeon` Resource Group
- [X] T007 [P] Create `terraform/variables.tf` with all input variables per contracts/terraform-contract.md: `resource_group_name` (default `"llm-dungeon"`), `azure_region` (default `"westeurope"`), `resource_prefix` (default `"llmdungeon"`), `tags`, `minimum_tls_version`, `azure_subscription_id`/`azure_tenant_id`/`azure_client_id`, `cosmos_consistency_level`/`cosmos_max_throughput`/`cosmos_backup_type`, `storage_account_replication_type`, `vnet_address_space`/`functions_subnet_prefix`/`private_endpoints_subnet_prefix`, `functions_hosting_plan`, `ai_foundry_model_name`/`ai_foundry_capacity`, `log_analytics_retention_days`, `budget_amount_usd`/`budget_alert_email`, `github_repository_owner`/`github_repository_name`/`github_repository_branch`
- [X] T008 [P] Create `terraform/backend.tf` (azurerm backend block) and `terraform/backend-prod.hcl` referencing the bootstrap-created Storage Account, per contracts/terraform-contract.md's Backend Configuration File
- [X] T009 [P] Add a `data "azurerm_resource_group" "rg"` lookup to `terraform/main.tf` referencing `var.resource_group_name`, per data-model.md's Resource Group entity — no `azurerm_resource_group` managed resource anywhere in this configuration
- [X] T010 [P] Create `terraform/network.tf` with `azurerm_virtual_network` (`10.0.0.0/16`) plus a Functions-integration subnet (`10.0.1.0/24`, delegated for Flex Consumption VNet integration) and a private-endpoints subnet (`10.0.2.0/24`, `private_endpoint_network_policies_enabled = false`) per data-model.md's Virtual Network entity
- [X] T011 [P] Create `terraform/outputs.tf` skeleton with `resource_group_name`, `resource_group_id`, `vnet_id`, `functions_subnet_id`, `private_endpoints_subnet_id` outputs per contracts/terraform-contract.md
- [X] T012 [P] Write `tests/infrastructure/test_terraform_validate.sh` wrapping `terraform fmt -check -recursive` and `terraform validate -json`
- [X] T013 Create `.github/workflows/terraform-validate.yml` invoking `tests/infrastructure/test_terraform_validate.sh` (T012) for the `fmt -check`/`validate` steps, plus `plan` on PR with artifact upload, per contracts/github-actions-contract.md; the `plan` step doubles as the automated drift check FR-016 and spec.md's Edge Cases require — a manually-changed resource surfaces as a non-empty plan rather than being silently reverted or accepted (depends on T012)
- [X] T014 [P] Create the `production` and `production-infra` GitHub environments via `gh api` (branch restricted to `main` on both), with a required-reviewer protection rule on `production-infra` only — done here, ahead of any workflow that targets them, so the approval gate is active from `terraform-apply.yml`'s first run rather than depending on a later user-story task; repository variable population stays a separate concern (T038)

**Checkpoint**: Backend, Resource Group lookup, VNet, variables, GitHub environments, and validate-CI are ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Infrastructure Is Provisioned Reproducibly via Terraform (Priority: P1) 🎯 MVP

**Goal**: An engineer applies the checked-in Terraform configuration and every required Azure resource for the environment exists, correctly configured, with no manual follow-up beyond the documented bootstrap.

**Independent Test**: From the pre-existing, empty `llm-dungeon` Resource Group, run `terraform apply` using the checked-in configuration and verify every required resource (Functions app, Storage accounts, Static Web App, Cosmos DB account, AI Foundry) exists, correctly configured, with no manual follow-up steps beyond the documented bootstrap.

### Implementation for User Story 1

- [X] T015 [P] [US1] Create `terraform/monitoring.tf` with `azurerm_log_analytics_workspace` (`PerGB2018` SKU, 30-day retention) per data-model.md's Log Analytics Workspace entity
- [X] T016 [US1] Extend `terraform/monitoring.tf` with a workspace-based `azurerm_application_insights` referencing the Log Analytics Workspace (depends on T015, same file)
- [X] T017 [US1] Extend `terraform/monitoring.tf` with `azurerm_consumption_budget_resource_group` ($50/month, 80%/100% email notification thresholds) per data-model.md's Budget & Cost Alert entity (depends on T015, same file)
- [X] T018 [US1] Add the Storage Account (Application Assets) to `terraform/main.tf` (`llmdungeonassetsprod`, `Standard`/`LRS`, TLS 1.2 minimum, public network access disabled, `assets` container) per data-model.md
- [X] T019 [US1] Add the Cosmos DB account, `llmdungeon-db-prod` database, and `stories` container to `terraform/main.tf` (serverless, `Session` consistency, `Periodic` backup, TLS 1.2 minimum, public network access disabled) per data-model.md (depends on T018, same file)
- [X] T020 [US1] Add the Azure AI Foundry / Azure OpenAI account and `gpt-4o-mini` model deployment (`capacity = 1`, i.e. 1,000 TPM) to `terraform/main.tf` per data-model.md (depends on T019, same file)
- [X] T021 [US1] Add the Azure Functions app to `terraform/main.tf`: Flex Consumption hosting plan, Python 3.11 on Linux, system-assigned Managed Identity, Entra ID auth required, TLS 1.2 minimum, VNet-integrated into the Functions-integration subnet (T010), with `app_settings` sourced from the Storage/Cosmos/AI Foundry/Application Insights resources' own attributes (no hardcoded values) per data-model.md (depends on T010, T015–T020, same file)
- [X] T022 [US1] Add the Azure Static Web App to `terraform/main.tf` (`Standard` SKU, linked to `RezaMahmood/llm-dungeon` on `main`) per data-model.md (depends on T021, same file)
- [X] T023 [US1] Complete `terraform/outputs.tf` with all remaining outputs (`functions_app_name`/`id`/`managed_identity_principal_id`, `static_web_app_name`/`id`/`url`, `storage_account_name`/`id`/`blob_endpoint`, `cosmos_db_account_name`/`id`/`endpoint`/`database_name`/`container_name`, `azure_openai_account_name`/`id`/`endpoint`/`deployment_name`, `application_insights_id`/`connection_string`/`instrumentation_key`, `log_analytics_workspace_id`, `budget_name`, `github_environment_variables` map) per contracts/terraform-contract.md (depends on T015–T022)
- [X] T024 [P] [US1] Create `.github/workflows/terraform-apply.yml` targeting the `production-infra` GitHub environment (Azure Login via the GitHub OIDC Managed Identity, `terraform init -backend-config=backend-prod.hcl`, `terraform apply`, capture outputs, required-reviewer approval gate scoped to this environment only — `backend-deploy.yml`/`frontend-deploy.yml` target the separate `production` environment and stay unapproved/automatic, per FR-010/SC-006) per contracts/github-actions-contract.md (depends on T014 — `production-infra` and its protection rule must already exist)
- [X] T025 [P] [US1] Write `tests/infrastructure/test_resource_creation.py` asserting every provisioned resource exists with its expected configuration (Functions Managed Identity enabled, Storage/Cosmos/AI Foundry public access disabled, VNet integration present) per contracts/github-actions-contract.md's Infrastructure Testing workflow
- [X] T026 [P] [US1] Create `.github/workflows/infrastructure-tests.yml` running `pytest tests/infrastructure/ -v` on a nightly schedule and on-demand (`workflow_dispatch`) per contracts/github-actions-contract.md
- [X] T027 [US1] Execute quickstart.md Scenario 1 (Bootstrap Terraform State Storage) and Scenario 2 (Provision Complete Production Infrastructure) end-to-end to validate User Story 1 independently (depends on T006–T026)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (MVP).

---

## Phase 4: User Story 2 - Application Code Deploys Automatically via GitHub Actions (Priority: P2)

**Goal**: A merged code change triggers a GitHub Actions workflow that builds and deploys the updated backend and/or frontend, with no manual upload or local deployment command.

**Independent Test**: Merge a change to `main` and verify the corresponding GitHub Actions workflow runs to completion and the updated code is live in production, with no manual deployment step.

### Implementation for User Story 2

- [X] T028 [P] [US2] Create `.github/workflows/backend-deploy.yml` (triggered on `backend/**` changes to `main` or `workflow_dispatch`; Python 3.11 setup, `pytest backend/tests/`, Azure Login via OIDC, `func pack --build remote`, deploy to the Functions app, post-deploy smoke test against the health endpoint) per contracts/github-actions-contract.md
- [X] T029 [P] [US2] Create `.github/workflows/frontend-deploy.yml` (triggered on `frontend/**` changes to `main` or `workflow_dispatch`; Node.js setup, `npm ci`, tests, build, deploy to the Static Web App) per contracts/github-actions-contract.md
- [ ] T030 [US2] Execute quickstart.md Scenario 7 (Full Deployment Pipeline Test) end-to-end to validate User Story 2 independently (depends on T028, T029)

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - GitHub Connects to Azure Without Stored Secrets (Priority: P3)

**Goal**: GitHub Actions workflows authenticate to Azure using federated OIDC anchored to the dedicated GitHub OIDC Managed Identity, with zero long-lived Azure credentials stored in GitHub.

**Independent Test**: Inspect the repository's configured secrets (none Azure-related should exist); inspect the Azure side and confirm the federated credential is on a Managed Identity, not an App Registration; trigger a deployment and confirm it authenticates via OIDC federation alone.

### Implementation for User Story 3

- [X] T031 [P] [US3] Write `tests/infrastructure/test_oidc_authentication.py` verifying (a) Azure CLI/SDK calls authenticate successfully via the GitHub OIDC Managed Identity's federated token, with zero stored credentials present and zero fallback to a stored secret, and (b) a deliberately misconfigured/missing federated credential subject causes authentication to fail clearly rather than falling back to a stored secret or proceeding unauthenticated, per contracts/github-actions-contract.md's Infrastructure Testing workflow (FR-011/FR-011a/FR-016/SC-004, spec.md US3 Acceptance Scenario 2)
- [ ] T032 [US3] Execute quickstart.md Scenario 3 (Validate Infrastructure via GitHub Actions) and Scenario 5 (Test GitHub → Azure OIDC Authentication) end-to-end, confirming no Azure secrets are stored in the GitHub repository and the GitHub OIDC Managed Identity's role assignment is scoped only to the `llm-dungeon` Resource Group (depends on T006, T031)

**Checkpoint**: User Stories 1, 2, AND 3 all work independently.

---

## Phase 6: User Story 4 - Backend Resources Communicate Privately and Without Stored Credentials (Priority: P4)

**Goal**: The Azure Functions backend reaches Storage, Cosmos DB, and AI Foundry exclusively over private network paths, authenticated with its Managed Identity — never a stored key, connection string, or API key.

**Independent Test**: With the backend deployed, verify calls to Storage, Cosmos DB, and AI Foundry succeed over a private endpoint and fail if attempted over the public internet, and that no access key/connection string/API key exists in the backend's configuration.

### Implementation for User Story 4

- [X] T033 [P] [US4] Create `terraform/identity.tf` with role assignments for the Functions app's system-assigned Managed Identity (`Storage Blob Data Contributor` on the assets Storage Account, `Cosmos DB Data Contributor` on the Cosmos DB account, `Cognitive Services User` on the AI Foundry account, `Monitoring Metrics Publisher` on Application Insights) per data-model.md's Managed Identity (Function App) entity
- [X] T034 [US4] Extend `terraform/network.tf` with private endpoints for the Storage Account, Cosmos DB account, and AI Foundry account, attached to the private-endpoints subnet (T010) per data-model.md's Private Endpoints entity (depends on T018–T020, T010; same file as T010)
- [X] T035 [US4] Extend `terraform/network.tf` with Private DNS Zones (`privatelink.blob.core.windows.net`, `privatelink.documents.azure.com`, `privatelink.openai.azure.com`) and their VNet links, per data-model.md's Private DNS Zones entity (depends on T034, same file)
- [X] T036 [P] [US4] Write `tests/infrastructure/test_private_connectivity.py` verifying DNS resolves Storage/Cosmos DB/AI Foundry hostnames to private IPs, connections succeed over the private endpoint, and connections attempted over the public endpoint are rejected
- [ ] T037 [US4] Execute quickstart.md Scenario 4 (Verify Private Connectivity) end-to-end to validate User Story 4 independently (depends on T033–T036)

**Checkpoint**: User Stories 1–4 all work independently.

---

## Phase 7: User Story 5 - Environment Configuration Is Externalized, Not Hardcoded (Priority: P5)

**Goal**: Azure resource names GitHub Actions needs come from GitHub environment variables; application configuration the backend needs comes from Function App application settings — neither hardcoded, no additional configuration service introduced.

**Independent Test**: Verify GitHub Actions workflows read Azure resource names from the GitHub environment's variables, not a hardcoded workflow value; change an application setting and verify the running backend picks it up without a code change or redeploy.

### Implementation for User Story 5

- [X] T038 [P] [US5] Create `scripts/configure-github-environment.sh` using `gh variable set --repo` (values sourced from `terraform output -json`) to populate the repository-level variables (`AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `RESOURCE_GROUP_NAME`, `FUNCTIONS_APP_NAME`, `STORAGE_ACCOUNT_NAME`, `COSMOS_ACCOUNT_NAME`, `STATIC_WEB_APP_NAME`, `TERRAFORM_VERSION`, `AZURE_PROVIDER_VERSION`) shared by both GitHub environments (T014 already created the environments and the `production-infra` protection rule), per contracts/deployment-config-contract.md
- [X] T039 [US5] Audit `.github/workflows/*.yml` (T013, T024, T026, T028, T029) to confirm every Azure resource name is read via `${{ vars.* }}` GitHub environment variables and none is a hardcoded literal; fix any found (depends on T013, T024, T026, T028, T029)
- [ ] T040 [US5] Execute quickstart.md Scenario 5 (Test GitHub → Azure OIDC Authentication env-var check) and Scenario 6 (Verify Application Settings & Configuration) end-to-end: change an application setting and confirm the backend picks it up with no code change or redeploy (depends on T038, T039)

**Checkpoint**: All five user stories are independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that span multiple user stories.

- [X] T041 [P] Run `terraform fmt -recursive` across `terraform/` and resolve any remaining `terraform validate` warnings
- [X] T042 [P] Update `README.md`/`docs/` with an infrastructure architecture overview linking to plan.md and quickstart.md
- [X] T043 Security review: confirm no hardcoded secrets, access keys, or connection strings exist anywhere in `terraform/`, `.github/workflows/`, `tests/infrastructure/`, or `scripts/` (Constitution Principles II and VII)
- [ ] T044 Execute all 8 quickstart.md scenarios end-to-end as a final full-feature validation pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories (nothing can be applied without a backend, Resource Group lookup, VNet, and the GitHub environments the workflows target)
- **User Stories (Phase 3–7)**: All depend on Foundational phase completion
  - US1 (P1) has no dependency on other stories — it is the MVP. Its `terraform-apply.yml` (T024) depends on T014 so the `production-infra` environment's approval gate is active from the first run, not added retroactively by US5
  - US2 (P2) depends on US1's Terraform resources existing (something to deploy into) but its own workflow files are independently authored
  - US3 (P3) depends on the GitHub OIDC Managed Identity from Foundational (T006); its test/validation tasks are independent of US1/US2's file contents
  - US4 (P4) depends on US1's Storage/Cosmos/AI Foundry resources existing (T018–T020) to attach private endpoints to
  - US5 (P5) depends on US1–US4's workflow and Terraform files existing to audit/configure against, and on T014 having already created the GitHub environments it populates variables into
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### Within Each User Story

- `terraform/main.tf` and `terraform/monitoring.tf` edits within US1 are strictly sequential (same file)
- `terraform/network.tf` edits within US4 are strictly sequential (same file, and depend on US1's resources existing)
- Test files (`tests/infrastructure/test_*.py`) and workflow files (`.github/workflows/*.yml`) are independent of each other and of the `.tf` files they exercise, so can be authored in parallel with the resources they will later validate

### Parallel Opportunities

- All Setup tasks marked [P] (T002–T005) can run in parallel
- Foundational tasks marked [P] (T006–T012, T014) touch distinct files/resources and can run in parallel; T013 depends on T012 (it invokes the script T012 writes)
- Once Foundational completes, US1's monitoring.tf (T015), test files (T025), and CI workflow (T024, T026) can proceed in parallel with each other, even while T018–T022 sequentially build out main.tf
- US2's two workflow files (T028, T029) can run in parallel
- US3's test file (T031) can be written in parallel with US1/US2/US4 work, once Foundational's OIDC identity (T006) exists
- US4's identity.tf (T033) and test file (T036) can run in parallel with each other and with network.tf's sequential T034→T035 chain

---

## Parallel Example: Foundational Phase

```bash
# Launch all Foundational file-creation tasks together (each touches a distinct file/resource):
Task: "Create scripts/bootstrap.sh implementing the Bootstrap Procedure"
Task: "Create terraform/variables.tf with all input variables"
Task: "Create terraform/backend.tf and terraform/backend-prod.hcl"
Task: "Add a data \"azurerm_resource_group\" \"rg\" lookup to terraform/main.tf"
Task: "Create terraform/network.tf with the Virtual Network and subnets"
Task: "Create terraform/outputs.tf skeleton"
Task: "Write tests/infrastructure/test_terraform_validate.sh"
Task: "Create the production and production-infra GitHub environments with production-infra's required-reviewer rule"

# T013 (terraform-validate.yml) runs after T012, since it invokes that script
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md Scenarios 1–2 independently
5. This alone delivers a reproducibly-provisioned Azure environment — the foundation every other feature in the project runs on

### Incremental Delivery

1. Setup + Foundational → backend, Resource Group lookup, VNet, and validate-CI ready
2. Add User Story 1 → `terraform apply` provisions the full stack → **MVP**
3. Add User Story 2 → code changes deploy automatically on merge
4. Add User Story 3 → confirm/validate the OIDC-only, no-stored-secrets connectivity already in place since Foundational
5. Add User Story 4 → backend traffic locked to private endpoints, Managed Identity only
6. Add User Story 5 → confirm/validate configuration externalization end-to-end
7. Polish → formatting, docs, security review, full quickstart validation

### Parallel Team Strategy

With multiple contributors, once Foundational is done:

- Contributor A: US1's `main.tf`/`monitoring.tf`/`outputs.tf` chain (T015–T023)
- Contributor B: US1's CI/test files (T024–T026), then US2 (T028–T030)
- Contributor C: US3's test file (T031–T032), then US4 (T033–T037)
- Contributor D: US5 (T038–T040), joining once US1–US4's files exist to audit

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story (US1–US5) for traceability
- `terraform/main.tf`, `terraform/monitoring.tf`, and `terraform/network.tf` each accumulate resources across phases — respect the noted same-file sequential chains within each
- `terraform-apply.yml` (T024) targets the `production-infra` GitHub environment, created with its required-reviewer rule by T014 (Foundational) so the gate is active from the first run; `backend-deploy.yml`/`frontend-deploy.yml` (T028, T029) target `production` (no approval), so application deploys stay fully automatic per FR-010/SC-006
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
