# Implementation Plan: Azure Infrastructure Provisioning

**Branch**: `007-azure-infrastructure-provisioning` | **Date**: 2026-08-28 | **Spec**: `specs/007-azure-infrastructure-provisioning/spec.md`

**Input**: Feature specification from `/specs/007-azure-infrastructure-provisioning/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Provision a complete Azure infrastructure stack (Functions, Storage, Cosmos DB, Static Web App, AI Foundry) via version-controlled Terraform configuration, with automated deployment via GitHub Actions using federated OIDC, private networking between backend resources, and environment configuration externalized to GitHub and Function App settings. The infrastructure supports one Production environment initially and is structured to allow future environment expansion without redesign.

## Technical Context

**Infrastructure as Code**: Terraform >= 1.5.0, Azure Provider >= 3.80.0 (resolved in research.md §1)

**Cloud Provider**: Microsoft Azure (exclusive hosting provider per Principle V)

**Primary Dependencies**: 
- Azure CLI / Terraform CLI / GitHub CLI (`gh`, for scripted environment/variable configuration)
- Azure Storage (backend state + application assets)
- Azure Cosmos DB (serverless, story configuration)
- Azure Functions (Python 3.11+ backend runtime per `002-login-and-access-control`)
- Azure Static Web App (frontend hosting)
- Azure AI Foundry (LLM resource with deployed model)
- GitHub Actions (CI/CD orchestration)
- Azure Entra ID (federated OIDC, authentication)
- Azure Managed Identity (user-assigned, for GitHub OIDC federation) and Azure Managed Identity (system-assigned, for Functions runtime auth) — two distinct identities

**Storage**: 
- Terraform remote state: dedicated Azure Storage account/container
- Application data: Cosmos DB (serverless)
- Assets: Azure Blob Storage
- Logs/telemetry: Azure Application Insights (observability)

**Testing**: 
- Terraform validate/plan/apply (infrastructure correctness)
- GitHub Actions workflow dry runs
- Connectivity assertions (private endpoint validation, OIDC authentication tests)
- pytest + `terraform validate`/`fmt` (resolved in research.md §2)

**Target Platform**: Azure cloud (multi-region capable, but single Production environment in-scope)

**Project Type**: Infrastructure as Code / DevOps deployment foundation

**Performance Goals**: N/A for infrastructure provisioning; Cosmos DB is serverless (auto-scaling); Functions auto-scaling per demand; Static Web App global CDN delivery

**Constraints**: 
- Private network paths for all backend resource communication (except Static Web App ↔ Function App, which uses public HTTPS with per-request Entra ID auth)
- Zero stored secrets (Managed Identity + federated OIDC only)
- Single Production environment minimum; structure must allow future staging/dev environments

**Scale/Scope**: 
- One Production environment (confirmed in-scope)
- ~5-10 named users, ~100-1000 requests/day, Cosmos DB serverless targeting ~1000 RU/s (auto-scale to 40,000 RU/s), Functions on Flex Consumption (resolved in research.md §3)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I - Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET (in-spec)
- FR-016 explicitly requires automated checks: `terraform validate`/`plan` in CI, deployment workflow dry runs, connectivity assertions
- Test/check plan will be defined in Phase 1 contracts (terraform validation harness, OIDC auth tests, private endpoint connectivity proofs)

### Principle II - Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET (in-spec)
- FR-011: No long-lived Azure credentials stored; federated OIDC only
- FR-011a: GitHub OIDC federated credential anchored to a dedicated user-assigned Managed Identity, not an App Registration/service principal
- FR-008: Managed Identity for all resource-to-resource auth
- Application requires Entra ID authentication per `002-login-and-access-control` spec
- Static Web App ↔ Function App public HTTPS connection is an explicit, documented exception (FR-014)

### Principle III - Defined Technology Stack (NON-NEGOTIABLE)
**Status**: ✓ SATISFIED (infrastructure layer)
- Backend: Python 3.11+ on Azure Functions (confirmed in prior specs)
- Frontend: ReactJS (confirmed in prior specs)
- Infrastructure as Code: Terraform (specified in input)
- This spec provisions the hosting layer; application stack defined elsewhere

### Principle IV - Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET (in-spec)
- One Production environment only (FR-013, confirmed in assumptions)
- Cosmos DB serverless (no manual throughput provisioning)
- Functions auto-scaling (no manual concurrency/reserve instances)
- No API Gateway, CDN cache layers, or read replicas beyond Static Web App's built-in CDN
- Structure allows future environments without redesign, but no over-provisioning now

### Principle V - Continuous Integration Gate (NON-NEGOTIABLE)
**Status**: ✓ MET (in-spec)
- FR-010: Deployment automated via GitHub Actions (no manual uploads)
- FR-016: Automated checks in CI (terraform validate/plan)
- Integration with `001-ci-cd-foundation` infrastructure is a dependency (not a violation)

### Principle VI - Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: ✓ SATISFIED (infrastructure layer)
- Terraform provisions Application Insights resource (assumption: Observability infrastructure)
- OpenTelemetry + Application Insights sink configured at application level (not infrastructure provisioning scope)
- LLM interaction telemetry is application-level, not infrastructure; infrastructure enables it by provisioning AI Foundry resource

### Principle VII - Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET (in-spec)
- FR-008: Managed Identity for Functions ↔ Storage, Cosmos DB, Azure AI Foundry auth
- FR-007: Private Link/Private Endpoints for all backend resource traffic (except documented Static Web App exception)
- No shared keys, connection strings, or API keys in backend configuration

### Principle VIII - UI Design System & Accessibility (NON-NEGOTIABLE)
**Status**: N/A (infrastructure layer — frontend screens built by other specs)
- This is an infrastructure/DevOps feature, not a player-facing or admin-facing UI
- Frontend implementation governed by other specs; infrastructure does not define UI

**GATES PASSED**: Constitution Check passes. No violations identified. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/007-azure-infrastructure-provisioning/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command) - Terraform best practices, Azure Private Link config, federated OIDC setup, Cosmos DB serverless tuning
├── data-model.md        # Phase 1 output (/speckit-plan command) - Entities: ResourceGroup, StorageAccount, CosmosDB, FunctionApp, StaticWebApp, PrivateEndpoint, ManagedIdentity
├── quickstart.md        # Phase 1 output (/speckit-plan command) - Validation scenarios: bootstrap storage, provision prod environment, trigger deployment, verify private connectivity, test OIDC flow
├── contracts/           # Phase 1 output (/speckit-plan command) - GitHub Actions workflow schema, Terraform variable/output contracts, deployment configuration schema
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Infrastructure Code (repository root)

```text
infrastructure/terraform/
├── main.tf              # Main resource definitions (Functions, Storage, Cosmos DB, Static Web App, AI Foundry)
├── network.tf           # Virtual Network, subnets, Functions VNet integration, private endpoints, DNS
├── monitoring.tf        # Log Analytics Workspace, Application Insights, Budget & cost alert
├── identity.tf          # Managed Identity role assignments
├── backend.tf           # Terraform remote state backend configuration
├── variables.tf         # Input variables (environment, resource naming, etc.)
├── outputs.tf           # Outputs for GitHub Actions consumption
├── locals.tf            # Local values and computed names
└── terraform.tfvars     # Environment-specific values (Production)

.github/workflows/
├── terraform-validate.yml      # PR check: terraform validate, format check
├── terraform-plan.yml          # PR step: terraform plan with artifact
├── terraform-apply.yml         # Main branch: terraform apply (infrastructure updates)
├── backend-deploy.yml          # Triggered by code changes: build & deploy Python Functions
├── frontend-deploy.yml         # Triggered by code changes: build & deploy Static Web App
└── infrastructure-tests.yml    # Infrastructure validation tests (connectivity, OIDC, private endpoint)

tests/infrastructure/
├── test_terraform_validate.sh  # terraform validate wrapper
├── test_private_connectivity.py    # Connectivity assertions to Storage, Cosmos, AI Foundry
├── test_oidc_authentication.py     # Federated OIDC flow validation
└── test_resource_creation.py       # Verify each resource exists post-apply
```

**Structure Decision**: Infrastructure as Code model using Terraform as the primary configuration language (specified in requirements), with GitHub Actions workflows for CI/CD orchestration. Terraform configuration is the source of truth for resource definitions. Application deployment workflows (backend Functions, frontend Static Web App) are separate from infrastructure provisioning but depend on the infrastructure being in place. Testing is split between Terraform validation (linting, syntax) and infrastructure behavior tests (connectivity, authentication).

## Complexity Tracking

> **No constitution violations identified — this section is omitted.**

---

## Phase 0: Outline & Research

### Identified Unknowns (NEEDS CLARIFICATION)

1. **Terraform & Azure Provider Version Constraints**
   - Current state: Spec requires Terraform but does not specify version pins or Azure Provider constraints
   - Research task: Determine minimum Terraform version, Azure Provider version, required features
   - Why needed: Version constraints affect state format, backend compatibility, resource attribute availability

2. **Testing & Infrastructure Validation Framework**
   - Current state: Spec mandates automated checks (FR-016) but does not specify testing tools/framework
   - Research task: Best practices for infrastructure testing (terraform test, terratest, Azure policy, Custom assertions)
   - Why needed: Determines how connectivity, OIDC, and resource-existence tests are implemented and executed

3. **Expected Scale & Throughput**
   - Current state: Spec does not provide request volume, Cosmos DB throughput, or Functions concurrency targets
   - Research task: Confirm with product/engineering: expected user count, requests/sec, Cosmos DB transactions/sec, concurrent function executions
   - Why needed: Affects Cosmos DB provisioning (RU/s), Functions scaling strategy, storage redundancy decisions

4. **Terraform State Backend Initialization**
   - Current state: Assumption mentions bootstrap step but does not detail the exact bootstrap procedure
   - Research task: Best practices for Terraform remote state bootstrap on Azure (initial manual creation vs. local-state init, naming, RBAC)
   - Why needed: Determines sequence of operations and documentation for first-time infrastructure setup

5. **Azure AI Foundry Deployment & Model Selection**
   - Current state: Spec requires AI Foundry resource with "at least one deployed language model" but model specifics are undefined
   - Research task: AI Foundry resource provisioning via Terraform, available models, deployment capacity/pricing, private endpoint configuration
   - Why needed: Determines Terraform resource declarations and whether additional configuration (model fine-tuning, content policies) is needed

6. **Private Endpoint & DNS Configuration**
   - Current state: Spec requires private endpoints for Storage, Cosmos DB, AI Foundry but does not specify DNS strategy (Azure Private DNS zones, host file, etc.)
   - Research task: Azure Private Link DNS best practices, Private DNS Zone setup, DNS resolution from Functions to backend resources
   - Why needed: Determines whether Private DNS Zones are provisioned by Terraform and how backend services resolve private endpoints

### Research Execution Plan

Research tasks will be conducted in parallel to resolve the unknowns above:

1. **Terraform Versioning & Azure Provider** → Identify stable, recent versions and document compatibility matrix
2. **Infrastructure Testing Framework** → Evaluate pytest (existing in project per `001-ci-cd-foundation`), terratest, Azure Policy, community practices
3. **Scale Confirmation** → Brief with engineering team on expected load, concurrency, and data volume
4. **Terraform State Bootstrap** → Document one-time bootstrap process and minimum manual steps required
5. **AI Foundry Integration** → Research Terraform Azure Provider support for Azure AI Foundry and model deployment
6. **Private Link & DNS** → Confirm DNS strategy (Private DNS Zones vs. alternatives) and implementation approach

---

## Phase 1: Design & Contracts

### Phase 1a: Data Model (entities and relationships)

**Entities to define** (extracted from spec and technical context):

1. **Terraform Configuration**
   - Purpose: Version-controlled declarative definition of Azure resources
   - Components: main.tf (resource definitions), variables.tf (inputs), outputs.tf (values for GitHub Actions), backend.tf (state configuration)

2. **Azure Resource Entities**
   - **Resource Group**: Single pre-existing Resource Group (`llm-dungeon`) that every project resource is provisioned into; referenced via a Terraform data source, never created/managed by Terraform
   - **Storage Account** (Terraform Backend): Remote state storage, separate from application storage
   - **Storage Account** (Application Assets): Blob storage for application assets, private endpoints
   - **Cosmos DB**: Serverless database for story configuration data, private endpoint, Managed Identity auth
   - **Azure Functions**: Backend execution environment, Managed Identity, private connectivity to dependencies
   - **Azure Static Web App**: Frontend hosting (public HTTPS from client, but backed by Entra ID-authenticated Function App)
   - **Azure AI Foundry**: LLM hosting resource with deployed model, private endpoint, Managed Identity auth
   - **Managed Identity (Function App)**: System-assigned identity for Functions, role assignments to Storage/Cosmos/Foundry
   - **Virtual Network**: Terraform-managed VNet (`10.0.0.0/16`) with a Functions-integration subnet and a private-endpoints subnet, created inside the pre-existing `llm-dungeon` Resource Group
   - **Private Endpoints**: Network connectivity from Functions to Storage, Cosmos, Foundry (no public paths)
   - **Log Analytics Workspace**: Backing workspace for workspace-based Application Insights (30-day retention)
   - **Azure Application Insights**: Observability/telemetry sink
   - **Budget & Cost Alert**: $50/month threshold on the `llm-dungeon` Resource Group with email notification
   - **GitHub Environments**: Repository-level variables for resource names, Azure subscription/tenant IDs, shared by two environments — `production` (app deploys, no approval, fully automatic per FR-010/SC-006) and `production-infra` (Terraform apply only, requires manual reviewer approval)

3. **Deployment Configuration Entities**
   - **GitHub Actions Workflow**: CI/CD pipeline definitions (infrastructure validation, application build/deploy)
   - **GitHub OIDC Managed Identity**: Dedicated user-assigned Managed Identity (not an App Registration) carrying the federated credential for GitHub ↔ Azure identity federation (repository, branch filters); created in the bootstrap step alongside the Terraform backend storage account, distinct from the Function App's Managed Identity
   - **Application Settings**: Function App configuration (resource names, telemetry keys, etc.)

4. **Relationships**
   - Functions → Storage/Cosmos/AI Foundry via Managed Identity (no keys/connection strings)
   - Private Endpoints → Backend resources (Storage, Cosmos, Foundry DNS names resolve to private IPs)
   - GitHub Actions → Azure via federated OIDC (no stored secrets)
   - Application Settings → Functions (environment-specific configuration)

### Phase 1b: Interface Contracts

The infrastructure project exposes contracts to:

1. **GitHub Actions Workflows**
   - **Inputs**: Terraform output values (resource names, endpoints, IDs), GitHub environment variables
   - **Outputs**: Deployment status, resource health, connection validation
   - **Schema**: Terraform outputs.tf → GitHub Actions environment variables (static web app URL, functions app name, etc.)

2. **Application Code (Backend/Frontend)**
   - **Inputs**: Application settings injected by Function App, environment variables
   - **Outputs**: Azure resource endpoints, authentication scopes, connection strings (where necessary)
   - **Schema**: Function App application settings → Python backend environment variables

3. **Terraform Consumption (IaC contracts)**
   - **Input Variables**: environment name, region, resource naming prefix, subscription/tenant IDs
   - **Output Values**: resource IDs, endpoints, connection details for downstream automation
   - **Schema**: variables.tf and outputs.tf define inputs/outputs for Terraform workflow

### Phase 1c: Validation Scenarios (quickstart.md)

The quickstart will document end-to-end validation for each user story:

1. **Scenario 1: Infrastructure Provisioned Reproducibly**
   - Setup: Pre-existing `llm-dungeon` Resource Group (empty of project resources), Terraform state bootstrap storage account created within it
   - Steps: `terraform apply` with production configuration
   - Validation: Verify Functions app, Storage, Cosmos DB, Static Web App, AI Foundry exist with correct configuration
   - Expected: All resources created without manual portal configuration

2. **Scenario 2: Code Deployment Automated**
   - Setup: Infrastructure in place, code change merged to main branch
   - Steps: Trigger backend or frontend deployment workflow
   - Validation: GitHub Actions workflow runs to completion, code deployed to Functions/Static Web App
   - Expected: Updated application live without manual upload

3. **Scenario 3: OIDC Authentication**
   - Setup: GitHub Actions workflow, federated OIDC trust configured
   - Steps: Run workflow step that authenticates to Azure (e.g., `azure/login` action)
   - Validation: Inspect GitHub secrets (none present), verify workflow authenticates successfully
   - Expected: Authentication succeeds via OIDC, no stored Azure credentials in GitHub

4. **Scenario 4: Private Connectivity**
   - Setup: Infrastructure provisioned, Functions backend deployed
   - Steps: Backend calls Storage, Cosmos DB, AI Foundry
   - Validation: Network flow inspection (private IP routing), connectivity test, public path blocked (if applicable)
   - Expected: All traffic over private endpoints, public access rejected

5. **Scenario 5: Environment Configuration**
   - Setup: GitHub environment variables and Function App settings configured
   - Steps: Backend reads application settings for Storage account name, Cosmos endpoint, etc.
   - Validation: Change an application setting, verify backend picks it up on next request (no code redeploy needed)
   - Expected: Configuration externalizes resource names and application values

---

---

## Phase 1: Design Artifacts Complete

✓ Phase 0 research complete: `research.md` generated with all unknowns resolved
✓ Phase 1 design complete:
  - `data-model.md`: All entities, relationships, and validation rules defined
  - `contracts/terraform-contract.md`: Input variables and output schema
  - `contracts/github-actions-contract.md`: CI/CD workflow specifications
  - `contracts/deployment-config-contract.md`: Application settings and bootstrap procedure
  - `quickstart.md`: 8 validation scenarios covering all user stories

---

## Constitution Re-Check (Post-Phase 1)

**Status**: ✓ PASSED (all principles satisfied by design)

### Principle I - Meaningful, Automated Testing
**Phase 1 Verification**: 
- Contracts specify infrastructure testing framework (pytest + terraform validate)
- GitHub Actions workflows include terraform validate/plan/apply steps
- Quickstart Scenario 8 documents nightly infrastructure validation tests
- Test coverage: connectivity, OIDC, resource creation

### Principle II - Secure-by-Default Access
**Phase 1 Verification**:
- Data model specifies Entra ID auth on all Functions endpoints
- No public access to backend resources (Storage, Cosmos, AI Foundry)
- Static Web App ↔ Functions uses public HTTPS with per-request Entra ID auth (documented exception, FR-014)
- Quickstart Scenario 5 validates OIDC authentication without stored secrets

### Principle III - Defined Technology Stack
**Phase 1 Verification**:
- Data model confirms Azure Functions (Python 3.11+) for backend
- Static Web App for ReactJS frontend
- Terraform as Infrastructure as Code tool (specified in requirements)

### Principle IV - Simplicity Over Premature Scale
**Phase 1 Verification**:
- Design targets one Production environment (no over-provisioning for unspecified environments)
- Cosmos DB serverless (auto-scaling, no manual RU/s tuning)
- Functions on Flex Consumption plan (pay-per-execution, no reserved capacity, native VNet integration)
- Storage LRS (no geo-redundancy for initial deployment)

### Principle V - Continuous Integration Gate
**Phase 1 Verification**:
- GitHub Actions contract specifies terraform-validate.yml for PR checks
- terraform-apply.yml only runs on main branch (after terraform-validate passes)
- All deployment workflows depend on infrastructure-apply.yml completing
- branch protection rules block merge while CI is not passing

### Principle VI - Observability & AI Cost Transparency
**Phase 1 Verification**:
- Data model includes Application Insights resource provisioning
- Application settings include APPLICATIONINSIGHTS_CONNECTION_STRING injection
- Backend configuration (deployment-config-contract.md) requires Python worker extensions for OpenTelemetry
- LLM interaction telemetry to be implemented at application level (infrastructure enables via Foundry provisioning)

### Principle VII - Zero-Trust Azure Resource Communication
**Phase 1 Verification**:
- Data model specifies Managed Identity for all resource authentication (Storage, Cosmos, AI Foundry)
- Private endpoints provisioned for all backend services
- No connection strings, keys, or API keys in configuration
- Terraform contract specifies private endpoint DNS zones
- Quickstart Scenario 4 validates private connectivity and disables public access

### Principle VIII - UI Design System & Accessibility
**Phase 1 Verification**:
- N/A (infrastructure layer, UI governed by other specs)

**GATES PASSED (POST-PHASE-1)**: All constitutional principles verified as satisfied by Phase 1 design. Design is ready for Phase 2 implementation (speckit-tasks command to generate tasks.md).

---

## Next Steps

1. **Phase 2 Planning**: Run `/speckit-tasks` command to generate `tasks.md` with implementation work breakdown
2. **Implementation**: Follow tasks.md to:
   - Create Terraform configuration files (main.tf, network.tf, identity.tf, etc.)
   - Create GitHub Actions workflows (.github/workflows/*.yml)
   - Create infrastructure tests (tests/infrastructure/*.py)
3. **Validation**: Execute quickstart scenarios to verify each feature works as specified
