# Feature Specification: Azure Infrastructure Provisioning

**Feature Branch**: `007-azure-infrastructure-provisioning`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "specify the infrastructure requirements. we will be using terraform to deploy azure functions and azure storage. We will be using azure static web to host the front end, azure blob storage for assets, cosmosdb serverless for storing story config data. we will need to provision azure storage for terraform backend. azure function to storage and cosmos should be via private link. deployments should be done with github actions. github should connect to azure using federated oidc. github environment variables should hold azure environment resource names. application variables should be part of application settings - no need for azure configuration service or key vault. managed identity should be used between azure functions and cosmos and storage. ask more questions on any other missing infrastructure related requirements."

**Split**: 2026-08-29 — this spec originally specified five user stories. It has been split so each resulting spec covers at most two: this spec now covers only "provision the resources" (Terraform) and "deploy code to them" (GitHub Actions). The keyless/private authentication requirements that were User Stories 3 and 4 now live in [015-keyless-azure-authentication-done](../015-keyless-azure-authentication-done/spec.md), and the externalized-configuration requirement that was User Story 5 now lives in [016-environment-configuration-externalization](../016-environment-configuration-externalization/spec.md). Both depend on the resources this spec provisions. Existing plan/tasks/contracts artifacts under this feature's implementation predate the split and are not re-scoped by it — see this checklist's Notes for implementation status.

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

### Edge Cases

- Terraform is run before its own remote-state storage account exists: this bootstrap step is handled distinctly from ordinary Terraform runs (see Assumptions), since Terraform cannot use a backend that doesn't exist yet.
- Two GitHub Actions workflow runs are triggered close together against the same environment: they do not corrupt Terraform state or leave the environment in a partially-applied state (state locking prevents concurrent apply).
- **Known gap (2026-08-29)**: the `production-infra` required-reviewer approval gate in front of `terraform apply` is not currently backed by a plan the reviewer has seen — see T045 in tasks.md.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All Azure infrastructure for this project MUST be defined as version-controlled Terraform configuration, capable of provisioning or updating every required resource for a given environment from that configuration alone.
- **FR-002**: A dedicated Azure Storage account and container to hold Terraform's own remote state, separate from any application storage, MUST exist before the main Terraform configuration runs. Since Terraform cannot use a backend that doesn't yet exist, this Storage account is created via a one-time bootstrap step (see Assumptions), not by the main Terraform configuration itself.
- **FR-003**: Terraform MUST provision an Azure Functions app to host the backend.
- **FR-004**: Terraform MUST provision an Azure Static Web App to host the frontend.
- **FR-005**: Terraform MUST provision an Azure Blob Storage resource for application asset storage, separate from the Terraform backend state storage account.
- **FR-006**: Terraform MUST provision a Cosmos DB account/database in serverless capacity mode for storing story configuration data.
- **FR-007**: Deployment of application code (backend and frontend) to Azure MUST be automated via GitHub Actions workflows, requiring no manual upload or local deployment command.
- **FR-008**: This infrastructure MUST support exactly one deployment environment (Production) at this time. The Terraform configuration and GitHub Actions workflows MUST be structured so that adding further environments later does not require redesigning them, even though only one is provisioned now.
- **FR-009**: Terraform MUST provision an Azure AI Foundry resource with at least one deployed language model, ready for the Azure Functions backend to call for the application's LLM needs. (How the backend authenticates to and reaches this resource is specified in `015-keyless-azure-authentication-done`.)
- **FR-010**: Each provisioned resource type and each infrastructure-pipeline outcome (successful infrastructure apply, drifted-resource plan, successful deployment) MUST have a corresponding automated check (e.g., `terraform validate`/`plan` in CI, a deployment workflow dry run) verifying its expected behavior.

### Key Entities

- **Terraform Configuration**: The version-controlled, declarative definition of every Azure resource this project needs, per environment.
- **Terraform Remote State**: The persisted record of what Terraform has provisioned, stored in a dedicated Azure Storage account/container distinct from application data.
- **Deployment Environment**: A named target (e.g., an environment such as development or production) with its own set of provisioned Azure resources and its own GitHub environment variables (see `016-environment-configuration-externalization`).
- **GitHub Actions Workflow**: An automated pipeline that builds and deploys application code to a target Deployment Environment. How it authenticates to Azure is specified in `015-keyless-azure-authentication-done`.
- **Azure AI Foundry Resource**: The provisioned LLM hosting resource, including at least one deployed language model, that the Function App calls for the application's narrative/LLM needs. How that call is authenticated and routed is specified in `015-keyless-azure-authentication-done`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer can provision a complete, working environment from a clean resource group using only the checked-in Terraform configuration, with no manual portal configuration beyond the documented one-time bootstrap step.
- **SC-002**: A merged, deployment-triggering change reaches its target environment through the automated workflow alone, with no manual deployment step performed by an engineer.

## Assumptions

- Terraform's own remote-state storage account is created via a small, one-time bootstrap step (run manually or via a minimal separate pipeline) before the main Terraform configuration can use it as a backend — this avoids the chicken-and-egg problem of a backend needing to already exist to store its own state.
- Standard, industry-typical settings apply for anything not explicitly specified here: Cosmos DB serverless with its default consistency/backup settings, HTTPS-only traffic, and clear resource naming.
- Terraform state locking (native to the Azure Storage backend) is relied upon to prevent concurrent applies from corrupting state; no additional locking mechanism is introduced.
- This spec covers infrastructure provisioning and deployment automation mechanics only; it does not redefine the application-level features that run on top of this infrastructure (see `001` through `013`), nor how the backend authenticates to what gets provisioned here (see `015-keyless-azure-authentication-done`) or how configuration values reach it (see `016-environment-configuration-externalization`).
- Observability infrastructure (Application Insights, Log Analytics) required by the project's constitution is provisioned as part of this same Terraform configuration, even though it is not itself a point of open question here.
- Only a single Production environment is provisioned at this time (confirmed); no dev/staging environments exist yet. Resource naming and Terraform/GitHub Actions structure should not preclude adding them later, but building them out is explicitly out of scope for this feature.
- Azure AI Foundry provisioning is in scope for this spec (confirmed): Terraform provisions the Foundry resource and at least one deployed model. Model selection, capacity/throughput sizing, and content-safety configuration for the deployed model are implementation details for planning, not fixed by this spec beyond "at least one deployed language model" being available.
- All Azure resources for this project — application resources and the Terraform backend state storage account alike — are provisioned into a single, pre-existing Resource Group (`llm-dungeon`), created out-of-band before any Terraform run. Terraform references this group but does not create, rename, or delete it.
