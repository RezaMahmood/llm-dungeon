---

description: "Task list for Keyless Azure Authentication"
---

# Tasks: Keyless Azure Authentication

**Input**: Design documents from `/specs/015-keyless-azure-authentication/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Context**: This spec was split out of `007-azure-infrastructure-provisioning` on
2026-08-29 as a documentation/scope boundary change — every requirement here (FR-001
through FR-005) was already implemented, deployed, and covered by automated tests as part
of `007`'s build, *before* the split occurred. There is no new implementation to do. This
task list therefore documents the implementation that already exists and records its
verification, rather than sequencing new build work. Every task below is checked off
because it was independently confirmed against the actual repository state (Terraform,
bootstrap script, test suite, CI workflow) while producing plan.md.

**Tests**: Automated tests already exist (`infrastructure/tests/test_oidc_authentication.py`,
`infrastructure/tests/test_private_connectivity.py`) satisfying FR-005 and constitution
Principle I; this list does not duplicate them as separate test-writing tasks, since writing
them is not needed.

**Organization**: Tasks are grouped by user story, matching spec.md's two user stories.

## Phase 1: Setup

**Purpose**: N/A — this spec adds no new project, dependency, or scaffolding; it reuses
`007-azure-infrastructure-provisioning`'s existing `infrastructure/` and `.github/workflows/`
trees in place.

- [x] T001 Confirm no new setup is required: `infrastructure/terraform/`, `infrastructure/scripts/`, and `infrastructure/tests/` already exist and are wired into CI (`.github/workflows/infrastructure-tests.yml`, `terraform-apply.yml`, `backend-deploy.yml`)

---

## Phase 2: Foundational

**Purpose**: N/A — the prerequisite resources this spec authenticates to/from (Function App,
Storage, Cosmos DB, AI Foundry, GitHub Actions workflows) are provisioned by
`007-azure-infrastructure-provisioning` and already exist; no blocking prerequisite work
belongs to this spec.

**Checkpoint**: Foundation already in place — verification of both user stories can proceed.

---

## Phase 3: User Story 1 - GitHub Connects to Azure Without Stored Secrets (Priority: P1) 🎯 MVP

**Goal**: GitHub Actions workflows authenticate to Azure via federated OIDC anchored to a
dedicated Azure Managed Identity, with zero long-lived Azure credentials stored in GitHub.

**Independent Test**: quickstart.md Scenarios 1-3.

### Verification for User Story 1

- [x] T002 [US1] Verify no Azure client secret/certificate/access key is stored in GitHub repository secrets or variables — confirmed via `gh secret list` / `gh variable list` pattern in quickstart.md Scenario 1; only non-secret `AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID` variables are present (FR-003)
- [x] T003 [US1] Verify the GitHub OIDC federated credential is configured on a dedicated user-assigned Managed Identity (`llmdungeon-github-oidc-identity-prod`), not a traditional Entra App Registration/service principal, in `infrastructure/scripts/bootstrap.sh` (FR-003a)
- [x] T004 [US1] Verify four federated credentials are registered on that identity, covering GitHub's distinct OIDC subject-claim shapes, in `infrastructure/scripts/bootstrap.sh` (research.md R2)
- [x] T005 [US1] Verify the GitHub OIDC Managed Identity's role assignment is scoped to the Resource Group only (`Contributor`, via `az role assignment create` in `infrastructure/scripts/bootstrap.sh`), not a broad subscription-level role (FR-003a)
- [x] T006 [US1] Verify the GitHub OIDC Managed Identity is distinct from the Function App's own Managed Identity (separate resources, separate role assignments), per `infrastructure/scripts/bootstrap.sh` vs. `infrastructure/terraform/identity.tf`
- [x] T007 [US1] Verify `.github/workflows/terraform-apply.yml` and `.github/workflows/backend-deploy.yml` authenticate via `azure/login@v2` using OIDC (`id-token: write` permission, `client-id`/`tenant-id`/`subscription-id` from repo variables, no `client-secret` input)
- [x] T008 [US1] Verify the success-path automated check: `infrastructure/tests/test_oidc_authentication.py::test_oidc_authentication_succeeds` acquires a valid Azure management token via the GitHub OIDC identity with zero stored credentials (FR-005)
- [x] T009 [US1] Verify the failure-path automated check: `infrastructure/tests/test_oidc_authentication.py::test_misconfigured_federated_credential_fails_clearly` raises `ClientAuthenticationError` for an unrecognized federated credential rather than falling back to a stored secret or proceeding unauthenticated (FR-005, Edge Case)

**Checkpoint**: User Story 1 is fully implemented and independently verified — GitHub-to-Azure keyless authentication works and is covered by automated checks.

---

## Phase 4: User Story 2 - Backend Resources Communicate Privately and Without Stored Credentials (Priority: P2)

**Goal**: The Azure Functions backend reaches Blob Storage, Cosmos DB, and Azure AI Foundry
exclusively over private network paths, authenticated via its Managed Identity — no stored
key, connection string, or API key.

**Independent Test**: quickstart.md Scenarios 4-7.

### Verification for User Story 2

- [x] T010 [P] [US2] Verify a Private Endpoint exists for Storage, Cosmos DB, and the AI Foundry/Cognitive Services account, attached to the private-endpoints subnet, in `infrastructure/terraform/network.tf` (FR-001)
- [x] T011 [P] [US2] Verify `public_network_access_enabled = false` on Storage, Cosmos DB, and the AI Foundry/Cognitive Services account in `infrastructure/terraform/main.tf` (FR-001)
- [x] T012 [US2] Verify the Function App's system-assigned Managed Identity holds `Storage Blob Data Contributor` on the storage account, Cosmos DB SQL RBAC Data Contributor on the Cosmos account, and `Cognitive Services User` on the AI Foundry account, in `infrastructure/terraform/identity.tf` (FR-002)
- [x] T013 [US2] Verify no Storage access key, Cosmos DB connection string, or Foundry API key is present in the Function App's `app_settings` in `infrastructure/terraform/main.tf` (FR-002)
- [x] T014 [US2] Verify the one documented exception (Static Web App → Function App over public HTTPS, protected by per-request Entra ID auth instead of network isolation) is limited to exactly the Function App's ingress in `infrastructure/terraform/main.tf` line 218 (FR-004)
- [x] T015 [US2] Verify the private-endpoint-approved automated check: `infrastructure/tests/test_private_connectivity.py::test_private_endpoint_connection_approved` (parametrized storage/cosmos/openai) confirms each connection state is `Approved` (FR-005)
- [x] T016 [US2] Verify the public-access-denied automated check: `infrastructure/tests/test_private_connectivity.py::test_public_data_plane_access_denied` (parametrized storage/cosmos/openai) confirms public calls are refused/timed out or return 401/403 (FR-005)
- [x] T017 [US2] Document the one gap the automated checks cannot close from outside the VNet (in-VNet DNS resolution to private IPs) as a manual step in quickstart.md Scenario 4, per research.md R5

**Checkpoint**: User Story 2 is fully implemented and independently verified — backend-to-resource keyless, private connectivity works and is covered by automated checks, with the one documented exception intact.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T018 Confirm `.github/workflows/infrastructure-tests.yml` runs both test files nightly and on `workflow_dispatch`, giving FR-005 continuous, ongoing verification rather than a one-time check
- [x] T019 Run quickstart.md end-to-end as this spec's Principle IX (user-verified acceptance) pass, confirming the already-built feature still behaves as intended on the current `main`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Already satisfied — nothing to build.
- **Foundational (Phase 2)**: Already satisfied by `007-azure-infrastructure-provisioning`.
- **User Story 1 (Phase 3)** and **User Story 2 (Phase 4)**: Both already implemented; independent of each other (GitHub-to-Azure vs. Function-App-to-backend-resources are separate authentication paths).
- **Polish (Phase 5)**: Depends on both user stories' verification being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on User Story 2.
- **User Story 2 (P2)**: No dependency on User Story 1 (both depend only on `007`'s already-provisioned resources).

### Parallel Opportunities

- T010/T011 (Private Endpoint existence, public access disabled) can be verified in parallel — different Terraform resource blocks.
- User Story 1 and User Story 2 verification (Phases 3 and 4) can proceed in parallel — they check independent authentication paths.

---

## Implementation Strategy

No implementation strategy is needed — both user stories are already fully built and
deployed. The only "strategy" here was verification: confirm each functional requirement
against the real Terraform/script/test/CI state (done, T001-T019), and re-run
quickstart.md as the ongoing acceptance check whenever this area of the infrastructure
changes.
