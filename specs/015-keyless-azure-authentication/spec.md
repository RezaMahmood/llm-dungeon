# Feature Specification: Keyless Azure Authentication

**Feature Branch**: `015-keyless-azure-authentication`

**Created**: 2026-08-29

**Status**: Draft

**Input**: Split out of `007-azure-infrastructure-provisioning` on 2026-08-29, so that spec covers at most two user stories. This spec covers the third and fourth user stories originally specified there — "GitHub Connects to Azure Without Stored Secrets" and "Backend Resources Communicate Privately and Without Stored Credentials" — grouped together because both are the same underlying requirement (no stored Azure credentials, ever) applied at two different points: GitHub-to-Azure (deployment/provisioning) and Function-App-to-backend-resources (runtime).

**Split**: This spec depends on the Azure resources provisioned by `007-azure-infrastructure-provisioning` (Functions app, Storage, Cosmos DB, Azure AI Foundry resource) and the GitHub Actions workflows defined there (User Story 2) already existing to authenticate.

## User Scenarios & Testing *(mandatory)*

<!--
  This is an infrastructure/platform feature rather than a player- or admin-facing one.
  The "users" here are the engineering team and the automated pipelines acting on their
  behalf; the value delivered is that no Azure credential, key, or connection string is
  ever stored anywhere in this project, at either the deployment layer or the runtime
  layer.
-->

### User Story 1 - GitHub Connects to Azure Without Stored Secrets (Priority: P1)

GitHub Actions workflows authenticate to Azure using federated OpenID Connect (OIDC) identity federation anchored to an Azure Managed Identity, so no long-lived Azure credentials or secrets are stored in GitHub at all.

**Why this priority**: This directly satisfies the project's security posture (no stored credentials where a keyless alternative exists) and is a prerequisite for `007-azure-infrastructure-provisioning`'s User Story 2 deployments to run securely.

**Independent Test**: Inspect the repository's configured secrets/credentials and verify no Azure client secret, certificate, or access key is present; inspect the Azure side and verify the federated credential is configured on a Managed Identity (not a traditional App Registration/service principal); trigger a deployment and verify it authenticates successfully via OIDC federation alone.

**Acceptance Scenarios**:

1. **Given** a GitHub Actions workflow that needs to act on Azure resources, **When** it runs, **Then** it authenticates using federated OIDC trust between GitHub and an Azure Managed Identity, with no Azure secret stored in GitHub.
2. **Given** the federated OIDC trust is misconfigured or missing for a given workflow run, **When** authentication is attempted, **Then** the run fails clearly at the authentication step rather than falling back to a stored secret or proceeding unauthenticated.
3. **Given** the Managed Identity used for GitHub OIDC federation, **When** its granted Azure role assignments are inspected, **Then** they are scoped to only what the deployment and Terraform-apply workflows actually need, not a broad, unscoped subscription-level role.

---

### User Story 2 - Backend Resources Communicate Privately and Without Stored Credentials (Priority: P2)

The Azure Functions backend reaches its Blob Storage asset store, its Cosmos DB story-data store, and its Azure AI Foundry LLM resource exclusively over private network paths, authenticating with its Managed Identity rather than any stored key, connection string, or API key.

**Why this priority**: This is the runtime enforcement of the project's zero-trust resource-communication requirement; it depends on the resources from `007-azure-infrastructure-provisioning`'s User Story 1 already existing.

**Independent Test**: With the backend deployed, verify (e.g., via network configuration inspection and a live call) that calls to Storage, Cosmos DB, and Azure AI Foundry succeed over a private endpoint and fail if attempted over the public internet, and that no access key, connection string, or API key exists in the backend's configuration.

**Acceptance Scenarios**:

1. **Given** the Azure Functions backend needs to read or write Blob Storage, **When** it does so, **Then** the call travels over a private network path and is authenticated using the backend's Managed Identity.
2. **Given** the Azure Functions backend needs to read or write Cosmos DB, **When** it does so, **Then** the call travels over a private network path and is authenticated using the backend's Managed Identity.
3. **Given** the Azure Functions backend needs to call the deployed model in Azure AI Foundry, **When** it does so, **Then** the call travels over a private network path and is authenticated using the backend's Managed Identity.
4. **Given** Storage, Cosmos DB, or Azure AI Foundry have public network access disabled, **When** a connection is attempted from outside the private network path, **Then** it is rejected.

---

### Edge Cases

- A private endpoint or DNS configuration is broken after a change, so the backend cannot reach Storage or Cosmos DB: this fails as a clear connectivity/configuration error rather than silently falling back to a public path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Network connectivity from the Azure Functions backend to the Blob Storage asset account, Cosmos DB, and the Azure AI Foundry resource MUST use Private Link (private endpoints), with public network access disabled on those resources except where an explicit, documented exception applies (see FR-004 for the one such exception).
- **FR-002**: The Azure Functions backend MUST authenticate to Blob Storage, Cosmos DB, and the Azure AI Foundry resource using a Managed Identity; no storage access keys, Cosmos DB connection strings, or Foundry API keys may be used for this communication.
- **FR-003**: GitHub Actions workflows MUST authenticate to Azure using federated OpenID Connect (OIDC) identity federation; no long-lived Azure credential or secret may be stored in GitHub for this purpose.
- **FR-003a**: The GitHub OIDC federated credential MUST be configured on an Azure user-assigned Managed Identity, not on a traditional Microsoft Entra App Registration/service principal. This Managed Identity MUST be dedicated to GitHub Actions federation (distinct from the Function App's own Managed Identity used in FR-002) and MUST be granted only the Azure role assignments its workflows actually require (e.g., Terraform apply and application deployment on the project's resource group), not a broad, unscoped subscription-level role.
- **FR-004**: The Static Web App frontend MUST connect to the Function App backend over standard public HTTPS. This is an explicit, documented exception to the private-connectivity default in FR-001: the Function App independently requires Entra ID-authenticated requests on every call (see `002-login-and-access-control`), so this path is protected by identity rather than network isolation.
- **FR-005**: Each keyless-authentication outcome (successful OIDC-authenticated GitHub Actions run, failed/missing OIDC authentication, private-endpoint-authenticated calls to Storage/Cosmos DB/Azure AI Foundry, and rejected public-network connection attempts to those resources) MUST have a corresponding automated check verifying its expected behavior.

### Key Entities

- **Managed Identity (Function App)**: The Azure-native identity assigned to the Function App, used for keyless authentication to Blob Storage, Cosmos DB, and Azure AI Foundry.
- **GitHub OIDC Managed Identity**: A dedicated Azure user-assigned Managed Identity carrying the federated credential trust with GitHub Actions, used by workflows to authenticate to Azure without a stored secret; scoped with only the role assignments deployment and Terraform-apply workflows require.
- **Private Endpoint**: The private networking construct connecting the Function App to Blob Storage, Cosmos DB, and Azure AI Foundry without traversing the public internet.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of backend-to-Storage, backend-to-Cosmos-DB, and backend-to-Azure-AI-Foundry traffic observed in testing travels over a private network path; zero successful connections occur over a public endpoint. (The Static Web App-to-Function-App path is the one deliberate exception, per FR-004.)
- **SC-002**: 100% of backend-to-Storage, backend-to-Cosmos-DB, and backend-to-Azure-AI-Foundry authentication observed in testing uses Managed Identity; zero stored access keys, connection strings, or API keys are present in configuration or code.
- **SC-003**: 100% of GitHub Actions deployments to Azure in testing authenticate via federated OIDC bound to a Managed Identity; zero long-lived Azure credentials are stored in GitHub, and zero traditional Entra App Registration/service principal credentials are used for this connectivity.

## Assumptions

- GitHub Actions authenticates to Azure via a federated credential on a dedicated user-assigned Managed Identity (confirmed), rather than a traditional Microsoft Entra App Registration/service principal with a federated credential. This Managed Identity is separate from the Function App's runtime Managed Identity (FR-002) since the two need different role assignments (deployment/Terraform-apply permissions vs. data-plane access to Storage/Cosmos DB/Foundry).
- The Static Web App-to-Function App connection intentionally uses public HTTPS rather than a private path (confirmed) — this is the one deliberate, documented exception to the private-connectivity default, justified by the Function App's independent, per-request Entra ID authentication requirement.
- Azure AI Foundry access follows the same private-endpoint/Managed-Identity pattern as every other backend dependency, consistent with `007-azure-infrastructure-provisioning`'s provisioning of that resource.
