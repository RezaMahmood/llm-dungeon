# Feature Specification: Azure Infrastructure Provisioning

**Feature Branch**: `007-azure-infrastructure-provisioning`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "specify the infrastructure requirements. we will be using terraform to deploy azure functions and azure storage. We will be using azure static web to host the front end, azure blob storage for assets, cosmosdb serverless for storing story config data. we will need to provision azure storage for terraform backend. azure function to storage and cosmos should be via private link. deployments should be done with github actions. github should connect to azure using federated oidc. github environment variables should hold azure environment resource names. application variables should be part of application settings - no need for azure configuration service or key vault. managed identity should be used between azure functions and cosmos and storage. ask more questions on any other missing infrastructure related requirements."

## User Scenarios & Testing *(mandatory)*

<!--
  This is an infrastructure/platform feature rather than a player- or admin-facing one.
  The "users" here are the engineering team and the automated pipelines acting on their
  behalf; the value delivered is a reproducible, secure, low-maintenance deployment
  foundation for every other feature in this project.
-->

### User Story 1 - Infrastructure Is Provisioned Reproducibly via Terraform (Priority: P1)

An engineer applies version-controlled Terraform configuration to stand up (or update) every Azure resource this project needs for a given environment, and gets a consistent, repeatable result — not a hand-configured, undocumented set of portal changes.

**Why this priority**: Every other capability in this project ultimately runs on top of this infrastructure. Without a reproducible way to provision it, nothing else can be reliably built, tested, or recovered.

**Independent Test**: From an empty resource group, run Terraform apply using the checked-in configuration and verify every required resource (Functions app, Storage accounts, Static Web App, Cosmos DB account) exists, correctly configured, with no manual follow-up steps beyond documented bootstrap.

**Acceptance Scenarios**:

1. **Given** version-controlled Terraform configuration and no existing resources for an environment, **When** an engineer applies it, **Then** all required Azure resources for that environment are created in a consistent, documented state.
2. **Given** an existing environment provisioned by Terraform, **When** the configuration is changed and re-applied, **Then** only the intended resources are updated, and unrelated resources are left unchanged.
3. **Given** a resource was changed manually outside of Terraform, **When** Terraform plan is next run, **Then** the drift is surfaced clearly rather than being silently reverted or silently accepted.

---

### User Story 2 - Application Code Deploys Automatically via GitHub Actions (Priority: P2)

A merged code change triggers a GitHub Actions workflow that builds and deploys the updated backend and/or frontend to the target Azure environment, without a person manually uploading files or running deployment commands locally.

**Why this priority**: Automated deployment is what makes the constitution's PR-gated CI requirement meaningful in practice — it depends on the infrastructure from User Story 1 already existing to deploy into.

**Independent Test**: Merge a change to the deployment branch and verify the corresponding GitHub Actions workflow runs to completion and the updated code is live in the target environment, with no manual deployment step.

**Acceptance Scenarios**:

1. **Given** a merged change intended for deployment, **When** the GitHub Actions workflow runs, **Then** it deploys the updated backend and/or frontend code to the correct Azure environment automatically.
2. **Given** a deployment workflow fails partway through, **When** it fails, **Then** it reports the failure clearly and does not leave the environment in an undetected broken state.

---

### User Story 3 - GitHub Connects to Azure Without Stored Secrets (Priority: P3)

GitHub Actions workflows authenticate to Azure using federated OpenID Connect (OIDC) identity federation anchored to an Azure Managed Identity, so no long-lived Azure credentials or secrets are stored in GitHub at all.

**Why this priority**: This directly satisfies the project's security posture (no stored credentials where a keyless alternative exists) and is a prerequisite for User Story 2's deployments to run securely.

**Independent Test**: Inspect the repository's configured secrets/credentials and verify no Azure client secret, certificate, or access key is present; inspect the Azure side and verify the federated credential is configured on a Managed Identity (not a traditional App Registration/service principal); trigger a deployment and verify it authenticates successfully via OIDC federation alone.

**Acceptance Scenarios**:

1. **Given** a GitHub Actions workflow that needs to act on Azure resources, **When** it runs, **Then** it authenticates using federated OIDC trust between GitHub and an Azure Managed Identity, with no Azure secret stored in GitHub.
2. **Given** the federated OIDC trust is misconfigured or missing for a given workflow run, **When** authentication is attempted, **Then** the run fails clearly at the authentication step rather than falling back to a stored secret or proceeding unauthenticated.
3. **Given** the Managed Identity used for GitHub OIDC federation, **When** its granted Azure role assignments are inspected, **Then** they are scoped to only what the deployment and Terraform-apply workflows actually need, not a broad, unscoped subscription-level role.

---

### User Story 4 - Backend Resources Communicate Privately and Without Stored Credentials (Priority: P4)

The Azure Functions backend reaches its Blob Storage asset store, its Cosmos DB story-data store, and its Azure AI Foundry LLM resource exclusively over private network paths, authenticating with its Managed Identity rather than any stored key, connection string, or API key.

**Why this priority**: This is the runtime enforcement of the project's zero-trust resource-communication requirement; it depends on the resources from User Story 1 already existing.

**Independent Test**: With the backend deployed, verify (e.g., via network configuration inspection and a live call) that calls to Storage, Cosmos DB, and Azure AI Foundry succeed over a private endpoint and fail if attempted over the public internet, and that no access key, connection string, or API key exists in the backend's configuration.

**Acceptance Scenarios**:

1. **Given** the Azure Functions backend needs to read or write Blob Storage, **When** it does so, **Then** the call travels over a private network path and is authenticated using the backend's Managed Identity.
2. **Given** the Azure Functions backend needs to read or write Cosmos DB, **When** it does so, **Then** the call travels over a private network path and is authenticated using the backend's Managed Identity.
3. **Given** the Azure Functions backend needs to call the deployed model in Azure AI Foundry, **When** it does so, **Then** the call travels over a private network path and is authenticated using the backend's Managed Identity.
4. **Given** Storage, Cosmos DB, or Azure AI Foundry have public network access disabled, **When** a connection is attempted from outside the private network path, **Then** it is rejected.

---

### User Story 5 - Environment Configuration Is Externalized, Not Hardcoded (Priority: P5)

Azure resource names needed by GitHub Actions workflows come from GitHub environment variables scoped to the target environment, and application configuration values consumed by the backend come from the Function App's application settings — neither is hardcoded into workflow files or application code, and no additional configuration service is introduced.

**Why this priority**: This keeps the same workflow and application code portable across environments without code changes; it's a refinement on top of the deployment mechanics already covered by earlier stories.

**Independent Test**: Verify the GitHub Actions workflow reads Azure resource names from the GitHub environment's variables rather than a hardcoded value in the workflow file; separately, change an application setting for the backend and verify the running application picks it up without a code change or redeploy.

**Acceptance Scenarios**:

1. **Given** a GitHub Actions workflow that needs an Azure resource name, **When** it runs, **Then** it reads that name from the GitHub environment's variables rather than a value hardcoded in the workflow file.
2. **Given** the backend needs an application configuration value, **When** it reads that value, **Then** it comes from the Function App's application settings, with no Azure App Configuration service or Key Vault involved.

---

### Edge Cases

- Terraform is run before its own remote-state storage account exists: this bootstrap step is handled distinctly from ordinary Terraform runs (see Assumptions), since Terraform cannot use a backend that doesn't exist yet.
- A required application setting is missing for a given environment: the backend fails fast with a clear startup error identifying the missing setting, rather than failing unpredictably at first use.
- Two GitHub Actions workflow runs are triggered close together against the same environment: they do not corrupt Terraform state or leave the environment in a partially-applied state (state locking prevents concurrent apply).
- A private endpoint or DNS configuration is broken after a change, so the backend cannot reach Storage or Cosmos DB: this fails as a clear connectivity/configuration error rather than silently falling back to a public path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All Azure infrastructure for this project MUST be defined as version-controlled Terraform configuration, capable of provisioning or updating every required resource for a given environment from that configuration alone.
- **FR-002**: A dedicated Azure Storage account and container to hold Terraform's own remote state, separate from any application storage, MUST exist before the main Terraform configuration runs. Since Terraform cannot use a backend that doesn't yet exist, this Storage account is created via a one-time bootstrap step (see Assumptions), not by the main Terraform configuration itself.
- **FR-003**: Terraform MUST provision an Azure Functions app to host the backend.
- **FR-004**: Terraform MUST provision an Azure Static Web App to host the frontend.
- **FR-005**: Terraform MUST provision an Azure Blob Storage resource for application asset storage, separate from the Terraform backend state storage account.
- **FR-006**: Terraform MUST provision a Cosmos DB account/database in serverless capacity mode for storing story configuration data.
- **FR-007**: Network connectivity from the Azure Functions backend to the Blob Storage asset account, Cosmos DB, and the Azure AI Foundry resource MUST use Private Link (private endpoints), with public network access disabled on those resources except where an explicit, documented exception applies (see FR-014 for the one such exception).
- **FR-008**: The Azure Functions backend MUST authenticate to Blob Storage, Cosmos DB, and the Azure AI Foundry resource using a Managed Identity; no storage access keys, Cosmos DB connection strings, or Foundry API keys may be used for this communication.
- **FR-009**: Application configuration values consumed by the backend MUST be provided via the Function App's application settings; no Azure App Configuration service or Key Vault is provisioned or required for this purpose.
- **FR-010**: Deployment of application code (backend and frontend) to Azure MUST be automated via GitHub Actions workflows, requiring no manual upload or local deployment command.
- **FR-011**: GitHub Actions workflows MUST authenticate to Azure using federated OpenID Connect (OIDC) identity federation; no long-lived Azure credential or secret may be stored in GitHub for this purpose.
- **FR-011a**: The GitHub OIDC federated credential MUST be configured on an Azure user-assigned Managed Identity, not on a traditional Microsoft Entra App Registration/service principal. This Managed Identity MUST be dedicated to GitHub Actions federation (distinct from the Function App's own Managed Identity used in FR-008) and MUST be granted only the Azure role assignments its workflows actually require (e.g., Terraform apply and application deployment on the project's resource group), not a broad, unscoped subscription-level role.
- **FR-012**: Azure resource names needed by GitHub Actions workflows MUST be supplied via GitHub environment variables scoped to the target deployment environment, not hardcoded in workflow files.
- **FR-013**: This infrastructure MUST support exactly one deployment environment (Production) at this time. The Terraform configuration and GitHub Actions workflows MUST be structured so that adding further environments later does not require redesigning them, even though only one is provisioned now.
- **FR-014**: The Static Web App frontend MUST connect to the Function App backend over standard public HTTPS. This is an explicit, documented exception to the private-connectivity default in FR-007: the Function App independently requires Entra ID-authenticated requests on every call (see `002-login-and-access-control`), so this path is protected by identity rather than network isolation.
- **FR-015**: Terraform MUST provision an Azure AI Foundry resource with at least one deployed language model, ready for the Azure Functions backend to call for the application's LLM needs.
- **FR-016**: Each provisioned resource type and each CI/CD pathway (successful infrastructure apply, drifted-resource plan, successful deployment, failed OIDC authentication, private-connectivity enforcement) MUST have a corresponding automated check (e.g., `terraform validate`/`plan` in CI, a deployment workflow dry run, a connectivity assertion) verifying its expected behavior.

### Key Entities

- **Terraform Configuration**: The version-controlled, declarative definition of every Azure resource this project needs, per environment.
- **Terraform Remote State**: The persisted record of what Terraform has provisioned, stored in a dedicated Azure Storage account/container distinct from application data.
- **Deployment Environment**: A named target (e.g., an environment such as development or production) with its own set of provisioned Azure resources and its own GitHub environment variables.
- **GitHub Actions Workflow**: An automated pipeline that builds and deploys application code to a target Deployment Environment, authenticating to Azure via federated OIDC bound to the GitHub OIDC Managed Identity.
- **Managed Identity (Function App)**: The Azure-native identity assigned to the Function App, used for keyless authentication to Blob Storage, Cosmos DB, and Azure AI Foundry.
- **GitHub OIDC Managed Identity**: A dedicated Azure user-assigned Managed Identity carrying the federated credential trust with GitHub Actions, used by workflows to authenticate to Azure without a stored secret; scoped with only the role assignments deployment and Terraform-apply workflows require.
- **Private Endpoint**: The private networking construct connecting the Function App to Blob Storage, Cosmos DB, and Azure AI Foundry without traversing the public internet.
- **Azure AI Foundry Resource**: The provisioned LLM hosting resource, including at least one deployed language model, that the Function App calls using its Managed Identity for the application's narrative/LLM needs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer can provision a complete, working environment from a clean resource group using only the checked-in Terraform configuration, with no manual portal configuration beyond the documented one-time bootstrap step.
- **SC-002**: 100% of backend-to-Storage, backend-to-Cosmos-DB, and backend-to-Azure-AI-Foundry traffic observed in testing travels over a private network path; zero successful connections occur over a public endpoint. (The Static Web App-to-Function-App path is the one deliberate exception, per FR-014.)
- **SC-003**: 100% of backend-to-Storage, backend-to-Cosmos-DB, and backend-to-Azure-AI-Foundry authentication observed in testing uses Managed Identity; zero stored access keys, connection strings, or API keys are present in configuration or code.
- **SC-004**: 100% of GitHub Actions deployments to Azure in testing authenticate via federated OIDC bound to a Managed Identity; zero long-lived Azure credentials are stored in GitHub, and zero traditional Entra App Registration/service principal credentials are used for this connectivity.
- **SC-005**: Changing an application configuration value for a given environment requires an application-settings update only — no application code change and no code redeployment.
- **SC-006**: A merged, deployment-triggering change reaches its target environment through the automated workflow alone, with no manual deployment step performed by an engineer.

## Assumptions

- Terraform's own remote-state storage account is created via a small, one-time bootstrap step (run manually or via a minimal separate pipeline) before the main Terraform configuration can use it as a backend — this avoids the chicken-and-egg problem of a backend needing to already exist to store its own state.
- Standard, industry-typical settings apply for anything not explicitly specified here: Cosmos DB serverless with its default consistency/backup settings, HTTPS-only traffic, and clear resource naming.
- Terraform state locking (native to the Azure Storage backend) is relied upon to prevent concurrent applies from corrupting state; no additional locking mechanism is introduced.
- This spec covers infrastructure provisioning and CI/CD deployment mechanics only; it does not redefine the application-level features that run on top of this infrastructure (see `001` through `008`).
- Observability infrastructure (Application Insights, Log Analytics) required by the project's constitution is provisioned as part of this same Terraform configuration, even though it is not itself a point of open question here.
- Only a single Production environment is provisioned at this time (confirmed); no dev/staging environments exist yet. Resource naming and Terraform/GitHub Actions structure should not preclude adding them later, but building them out is explicitly out of scope for this feature.
- The Static Web App-to-Function App connection intentionally uses public HTTPS rather than a private path (confirmed) — this is the one deliberate, documented exception to the private-connectivity default, justified by the Function App's independent, per-request Entra ID authentication requirement.
- Azure AI Foundry provisioning is in scope for this spec (confirmed): Terraform provisions the Foundry resource and at least one deployed model, reachable from the Function App only via Managed Identity over a private endpoint, consistent with every other backend dependency.
- Model selection, capacity/throughput sizing, and content-safety configuration for the deployed model are implementation details for planning, not fixed by this spec beyond "at least one deployed language model" being available.
- GitHub Actions authenticates to Azure via a federated credential on a dedicated user-assigned Managed Identity (confirmed), rather than a traditional Microsoft Entra App Registration/service principal with a federated credential. This Managed Identity is separate from the Function App's runtime Managed Identity (FR-008) since the two need different role assignments (deployment/Terraform-apply permissions vs. data-plane access to Storage/Cosmos DB/Foundry).
- All Azure resources for this project — application resources and the Terraform backend state storage account alike — are provisioned into a single, pre-existing Resource Group (`llm-dungeon`), created out-of-band before any Terraform run. Terraform references this group but does not create, rename, or delete it.
