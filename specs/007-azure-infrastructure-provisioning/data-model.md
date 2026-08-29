# Data Model: Azure Infrastructure Provisioning

**Date**: 2026-08-28 | **Status**: Phase 1 Complete

## Core Entities

### 1. Terraform Configuration

**Purpose**: Version-controlled declarative definition of all Azure resources and their relationships.

**Components**:
- `main.tf`: Primary resource definitions (Functions, Storage, Cosmos DB, Static Web App, AI Foundry, roles, assignments)
- `network.tf`: Virtual Network and subnets, Functions VNet integration, private endpoints, Private DNS Zones, virtual network links, network rules
- `monitoring.tf`: Log Analytics Workspace, Application Insights, Budget & cost alert
- `identity.tf`: Managed Identity creation, role assignments (Reader, Blob Data Contributor, Cosmos DB contributor)
- `variables.tf`: Input variables (environment, region, resource naming, Azure subscription/tenant IDs, tags)
- `outputs.tf`: Exported values for GitHub Actions workflows and downstream consumption
- `locals.tf`: Computed values, naming conventions, common tags
- `backend.tf`: Backend configuration (Azure Storage account, container, key)
- `terraform.tfvars`: Environment-specific values (Production)

**Validation Rules**:
- All resource names follow naming convention: `{prefix}-{resource-type}-{environment}` (e.g., `llmdungeon-func-prod`), **except Storage Accounts**, which use a hyphen-free variant `{prefix}{resource-type}{environment}` (e.g., `llmdungeonassetsprod`) since Azure Storage Account names may not contain hyphens
- All resources are tagged with `environment=production`, `managed_by=terraform`, `project=llm-dungeon`, `application=llm-dungeon`, and `owner=Reza Mahmood`
- No hardcoded secrets or credentials in configuration files

**State Transitions**:
- Initial: No infrastructure exists → `terraform apply` → resources created
- Update: Configuration changed → `terraform plan` → review → `terraform apply` → resources updated
- Destroy: Manual `terraform destroy` (with approval) → all resources deleted

---

### 2. Azure Resource Entities

#### Resource Group
**Purpose**: The single Azure Resource Group that every resource for this project — application resources and the Terraform backend state storage account alike — is provisioned into.

**Properties**:
- `name`: `llm-dungeon` (fixed; pre-existing)
- `management`: Pre-created out-of-band (e.g., by a subscription owner) before any bootstrap or Terraform run; Terraform references it via a `data "azurerm_resource_group"` data source and never creates, modifies, or deletes it

**Validation Rules**:
- Bootstrap and Terraform both fail fast with a clear error if the `llm-dungeon` Resource Group does not already exist (never auto-created)
- No `azurerm_resource_group` managed resource exists in the Terraform configuration for this project

---

#### Storage Account (Terraform Backend)
**Purpose**: Remote state storage for Terraform itself (separate from application storage)

**Properties**:
- `account_name`: `{prefix}tstate{env}` — hyphen-free pattern, since Storage Account names may not contain hyphens (e.g., `llmdungeontstateprod`)
- `account_tier`: `Standard`
- `replication_type`: `LRS` (locally redundant; GRS available if geo-redundancy needed)
- `access_tier`: `Hot`
- `https_required`: `true`
- `minimum_tls_version`: `TLS1_2`
- `public_network_access`: `Enabled` — deliberately not `Disabled` (unlike the application Storage Account below): this account is created before any VNet exists and must be reachable from GitHub-hosted runners and developer machines, neither of which have a private network path to it. Access is still gated by Azure AD auth (`use_azuread_auth` in backend.tf), never anonymous or shared-key.
- `container_name`: `terraform-state`

**Validation Rules**:
- Must exist before main Terraform configuration applies (bootstrap step)
- No storage account keys used anywhere; `terraform init`/`plan`/`apply` and the bootstrap script authenticate via Azure AD (the operator's `az login` session or the GitHub OIDC Managed Identity), never a key

**Access Control**:
- Only GitHub Actions runner (via the GitHub OIDC Managed Identity) and bootstrap operator (via Azure CLI) can access

---

#### Storage Account (Application Assets)
**Purpose**: Blob storage for application-generated or static assets (images, documents, etc.)

**Properties**:
- `account_name`: `{prefix}assets{env}` — hyphen-free pattern, since Storage Account names may not contain hyphens (e.g., `llmdungeonassetsprod`)
- `account_tier`: `Standard`
- `replication_type`: `LRS`
- `access_tier`: `Hot`
- `https_required`: `true`
- `minimum_tls_version`: `TLS1_2`
- `public_network_access`: `Disabled`
- `container_name`: `assets`

**Validation Rules**:
- All network access must route through private endpoint
- Public endpoint exists but has default action = `Deny` with no IP/VNet allow-list

**Relationships**:
- Private endpoint: Storage account container endpoint
- DNS: `{account}.blob.core.windows.net` → Private DNS Zone A record (private IP)
- Authentication: Azure Functions Managed Identity (Reader + Blob Data Contributor roles)

**Access Control**:
- Azure Functions (Managed Identity): Read/Write to assets container
- Cosmos DB: No direct access (data is configuration, not assets)

---

#### Cosmos DB Account
**Purpose**: Serverless database for story configuration data (adventures, gameplay state, player progress).

**Properties**:
- `account_name`: `{prefix}-cosmos-{env}`
- `region`: `uksouth` — **not** the project's `azure_region` (`westeurope`), which every other resource uses. `westeurope` is confirmed out of Cosmos DB capacity (Azure returns `ServiceUnavailable`/"high demand ... zonal redundant ... cannot fulfill your request at this time" on every create attempt, reproduced via a direct `az cosmosdb create` probe unrelated to Terraform). `uksouth` was probed and confirmed to have capacity before committing to it. Private Link/private endpoints work cross-region, so the VNet and every other resource stay in `westeurope`; only Cosmos's data plane lives in `uksouth`.
- `offer_type`: `Standard` (supports serverless)
- `kind`: `GlobalDocumentDB`
- `consistency_level`: `Session` (confirmed; suitable for game state)
- `public_network_access_enabled`: `false`
- `minimum_tls_version`: `Tls12`
- `backup.type`: `Periodic` (confirmed), `interval_in_minutes: 240`, `retention_in_hours: 168` (every 4h, 7-day retention — Azure's own defaults, but must now be set explicitly; the API rejects `type: Periodic` with no interval/retention)
- `automatic_failover_enabled`: `false`, `multiple_write_locations_enabled`: `false`, single `geo_location` block with `zone_redundant: false` — single region, single write region, no Availability Zone redundancy; this project's scale (~5-10 users) needs none of it, and AZ capacity is exactly what's constrained in `westeurope` anyway
- Database: `{prefix}-db-prod`
- Container: `stories` (story configuration documents)

**Validation Rules**:
- Serverless auto-scaling enabled (RU/s auto-scales up to 40,000)
- All connections must use private endpoint
- No connection strings or keys in configuration; Managed Identity auth only

**Relationships**:
- Private endpoint: Cosmos DB account endpoint
- DNS: `{account}.documents.azure.com` → Private DNS Zone A record (private IP)
- Authentication: Azure Functions Managed Identity (Cosmos DB contributor role)

**Access Control**:
- Azure Functions (Managed Identity): Read/Write to stories container
- Static Web App: No direct access (calls via Functions backend)

---

#### Azure Functions
**Purpose**: Backend execution environment for game logic, LLM integration, and API endpoints.

**Properties**:
- `app_name`: `{prefix}-func-{env}`
- `hosting_plan`: `Flex Consumption` (confirmed) — pay-per-execution, native VNet integration for reaching private endpoints, no reserved capacity
- `runtime_version`: `~4` (Functions runtime v4)
- `python_version`: `3.11`
- `os_type`: `Linux`
- `auth_enabled`: `true` (Entra ID required, per Principle II)
- `managed_identity_enabled`: `true`
- `https_only`: `true`
- `minimum_tls_version`: `1.2`
- `vnet_integration_subnet`: The Functions-integration subnet of the [Virtual Network](#virtual-network) (see below) — required for FR-007 private connectivity to Storage/Cosmos DB/AI Foundry

**Validation Rules**:
- No anonymous access; all endpoints require Entra ID authorization
- Managed Identity is system-assigned
- Application settings injected at runtime (no code changes needed for environment switching)
- Outbound traffic to Storage/Cosmos DB/AI Foundry routes through the VNet integration subnet, never the public internet

**Environment Configuration** (Application Settings):
- `COSMOS_ENDPOINT`: Private endpoint URL (injected by Terraform)
- `COSMOS_DATABASE`: Database name
- `COSMOS_CONTAINER`: Container name
- `STORAGE_ACCOUNT_URL`: Private endpoint URL (injected by Terraform)
- `STORAGE_CONTAINER`: Asset container name
- `APPLICATIONINSIGHTS_CONNECTION_STRING`: Application Insights telemetry sink
- `AZURE_OPENAI_ENDPOINT`: Private endpoint URL (injected by Terraform)
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Model deployment name
- `PYTHON_ENABLE_WORKER_EXTENSIONS`: `true` (for OpenTelemetry support)

**Relationships**:
- Managed Identity: Assigned role assignments (Storage, Cosmos DB, AI Foundry)
- Private endpoints: Accesses Storage, Cosmos DB, AI Foundry over private connections
- Static Web App: Backend for frontend requests (public HTTPS, Entra ID auth per request)

---

#### Azure Static Web App
**Purpose**: Global CDN-backed frontend hosting for ReactJS application.

**Properties**:
- `name`: `{prefix}-web-{env}`
- `sku`: `Standard` (custom domains, staging environments)
- `repository_provider`: `GitHub`
- `repository_owner`: GitHub org/user
- `repository_name`: Repository name
- `repository_branch`: `main` (auto-deploy from main)
- `auth_enabled`: Managed by application (MSAL login flow)
- `https_only`: `true`

**Validation Rules**:
- Must be linked to GitHub repository for auto-deploy
- Backend function URL configured via API backend link (Static Web App → Function App)
- Entra ID authentication handled by frontend (MSAL) and backend (per-request validation)

**Relationships**:
- Backend: Linked to Azure Functions backend (CORS configured, API prefix set)
- Authentication: Entra ID via MSAL (client-side login, server-side validation)

**Access Control**:
- Public internet: Can reach Static Web App domain
- Entra ID: Only authenticated, authorized users access content
- Function App: Static Web App calls Functions via public HTTPS + Entra ID bearer token

---

#### Azure AI Foundry / Azure OpenAI Service
**Purpose**: LLM hosting and inference for game narrative/dungeon generation.

**Properties**:
- `name`: `{prefix}-openai-{env}`
- `kind`: `OpenAI`
- `account_name`: `{prefix}-ai-{env}`
- `sku_name`: `S0` (Standard tier; supports provisioned throughput)
- `public_network_access_enabled`: `false`

**Deployments** (Models):
- `deployment_name`: `gpt-4o-mini`
- `model_name`: `gpt-4o-mini`
- `model_version`: Latest stable (`2024-07-18` at time of provisioning)
- `scale_type`: `DataZoneStandard` — a plain region-pinned `Standard` SKU is no longer offered for this model in `westeurope` (Azure now only exposes `Global*`/`DataZone*` SKUs for it). `DataZoneStandard` was chosen over `GlobalStandard` at the time (keeping inference traffic within the EU data zone, closer to the region-pinned behavior `Standard` would have had); with the data-residency requirement since confirmed unnecessary (region choice is proximity-only), `GlobalStandard` would now be an equally acceptable choice — not changed here since `DataZoneStandard` is already live and working, but worth revisiting if `GlobalStandard` offers better availability/pricing later
- `capacity`: `1` (Terraform's `azurerm_cognitive_deployment` capacity unit = 1,000 TPM, so `capacity = 1` provisions 1,000 TPM / 1K TPM; can scale up later without redesign)

**Validation Rules**:
- Model deployment must exist before Functions can call LLM
- All calls authenticated via Managed Identity (bearer token)
- Rate limits enforced by Azure (no additional rate-limiting in application code)

**Relationships**:
- Private endpoint: AI Foundry account endpoint
- DNS: `{account}.openai.azure.com` → Private DNS Zone A record (private IP)
- Authentication: Azure Functions Managed Identity (Azure Cognitive Services User role)

**Access Control**:
- Azure Functions (Managed Identity): Call deployed models (inference)
- Static Web App: No direct access (calls via Functions backend)

---

#### Managed Identity (Function App)
**Purpose**: Keyless authentication for Azure Functions to access Storage, Cosmos DB, AI Foundry. Distinct from the [GitHub OIDC Managed Identity](#github-oidc-managed-identity), which is a separate identity dedicated to GitHub Actions deployment/Terraform-apply permissions.

**Properties**:
- `type`: System-assigned (created with Functions app)
- `principal_id`: Unique ID for Functions app

**Role Assignments**:
- **Storage Account**: 
  - Role: `Storage Blob Data Contributor` (read/write to assets)
  - Scope: Application Storage account
- **Cosmos DB**:
  - Role: `Cosmos DB Data Contributor` (read/write to stories database)
  - Scope: Cosmos DB account
- **AI Foundry**:
  - Role: `Cognitive Services User` (call LLM models)
  - Scope: Azure OpenAI Service account
- **Application Insights**:
  - Role: `Monitoring Metrics Publisher` (send telemetry)
  - Scope: Application Insights resource

**Validation Rules**:
- Role assignments must be in place before Functions can access resources
- No access keys or connection strings stored anywhere

---

#### Virtual Network
**Purpose**: Provides the private address space that Functions VNet-integrates into and that private endpoints attach to, so backend traffic never traverses the public internet. Created by Terraform (confirmed) inside the `llm-dungeon` Resource Group — unlike the Resource Group itself, this is Terraform-managed, not pre-existing.

**Properties**:
- `name`: `{prefix}-vnet-{env}`
- `address_space`: `10.0.0.0/16`

**Subnets**:
- **Functions integration subnet**: `10.0.1.0/24` — delegated to `Microsoft.App/environments` (Flex Consumption VNet integration delegation), used by Azure Functions for outbound connectivity
- **Private endpoints subnet**: `10.0.2.0/24` — hosts the private endpoints for Storage, Cosmos DB, and AI Foundry; `private_endpoint_network_policies_enabled = false`

**Validation Rules**:
- Both subnets must exist before Functions VNet integration or private endpoints can be created
- Address ranges must not overlap with any peered/on-premises network (none exist currently; noted for future-proofing)

---

#### Private Endpoints
**Purpose**: Network connectivity from Azure Functions to backend resources (Storage, Cosmos DB, AI Foundry) without traversing public internet.

**Components**:

**Storage Private Endpoint**:
- `service_name`: `{storage_account_name}`
- `subresource_name`: `blob` (for Blob Storage)
- `private_ip_address`: Assigned by Azure (usually x.x.x.{10-20} in subnet)
- DNS: `storageaccount.blob.core.windows.net` → private IP (via Private DNS Zone)

**Cosmos DB Private Endpoint**:
- `service_name`: `{cosmos_account_name}`
- `subresource_name`: `Sql` (for Cosmos DB SQL API)
- `private_ip_address`: Assigned by Azure
- DNS: `account.documents.azure.com` → private IP (via Private DNS Zone)

**AI Foundry Private Endpoint**:
- `service_name`: `{openai_account_name}`
- `subresource_name`: `account` (for Azure OpenAI)
- `private_ip_address`: Assigned by Azure
- DNS: `account.openai.azure.com` → private IP (via Private DNS Zone)

**Validation Rules**:
- Private endpoint must be in the same region as Functions (or VNet-linked region)
- DNS zones must be linked to Functions' VNet for name resolution
- Public endpoint exists on each resource but has firewall rules denying all traffic (default_action = Deny)

---

#### Private DNS Zones
**Purpose**: DNS name resolution for private endpoints (returns private IPs instead of public IPs).

**Zones**:
- `privatelink.blob.core.windows.net` (Storage)
- `privatelink.documents.azure.com` (Cosmos DB)
- `privatelink.openai.azure.com` (AI Foundry)

**Configuration**:
- A records: Created automatically when private endpoint is configured
  - E.g., `storageaccount.blob.core.windows.net` → `10.0.1.15` (private IP)
- Virtual network links: Link each zone to Functions VNet (enablement for DNS resolution)

**Validation Rules**:
- VNet link must exist before Functions can resolve private endpoint names
- Zone records updated automatically when private endpoint is created/deleted

---

#### GitHub Actions Environments
**Purpose**: CI/CD context and configuration for deployment pipelines. Split into two environments (confirmed) so the required-reviewer approval gate covers infrastructure changes only, never application code deployments — otherwise FR-010/SC-006's "no manual deployment step" guarantee would be broken for routine app deploys.

**Properties**:
- `production`: used by `backend-deploy.yml`, `frontend-deploy.yml`, `infrastructure-tests.yml` — **no** required reviewers; deploys run fully automatically on merge
- `production-infra`: used by `terraform-apply.yml` only — **required reviewer** configured; a human must approve before `terraform apply` runs against Azure
- Deployment branches (both): `main` only
- Environment variables — defined once at the **repository** level, not duplicated per environment (both environments' workflows need the same values, none are secrets):
  - `AZURE_SUBSCRIPTION_ID`: Azure subscription ID
  - `AZURE_TENANT_ID`: Entra ID tenant ID
  - `AZURE_CLIENT_ID`: GitHub OIDC Managed Identity client ID
  - `RESOURCE_GROUP_NAME`: Azure Resource Group name
  - `FUNCTIONS_APP_NAME`: Azure Functions app name
  - `STORAGE_ACCOUNT_NAME`: Application Storage account name
  - `COSMOS_ACCOUNT_NAME`: Cosmos DB account name
  - `STATIC_WEB_APP_NAME`: Static Web App name
  - `TERRAFORM_VERSION`: Terraform version to use (pinned)
  - `AZURE_PROVIDER_VERSION`: Azure Provider version (pinned)

**Validation Rules**:
- Repository variables are public (no secrets)
- Federated OIDC trust configured between GitHub repo and the dedicated GitHub OIDC Managed Identity, matched on branch ref (not environment name), so the same credential authenticates jobs in both environments
- `production-infra` is protected by require-approval and require-status-checks; `production` is protected by require-status-checks only (no approval)

---

#### GitHub OIDC Managed Identity
**Purpose**: Dedicated Azure user-assigned Managed Identity that carries the federated credential trust with GitHub Actions, enabling GitHub Actions to authenticate to Azure without storing credentials. Distinct from the Functions app's runtime Managed Identity (see [Managed Identity](#managed-identity)) because it needs different role assignments — deployment/Terraform-apply permissions on the resource group, not data-plane access to Storage/Cosmos DB/AI Foundry.

**Properties**:
- `identity_type`: User-assigned Managed Identity
- `role_assignments`: Scoped to the resource group only what deployment and Terraform-apply workflows require (e.g., Contributor on the resource group) — not a broad, unscoped subscription-level role
- **Two** federated credentials (not one) — GitHub's OIDC subject claim differs by trigger type, so one credential per shape. This repo also issues subjects in the newer immutable-ID format (`repo:OWNER@ownerID/REPO@repoID:...`), not the classic name-only format — discovered when a name-only subject still failed `AADSTS700213` after correctly splitting by trigger type; `scripts/bootstrap.sh` fetches the owner/repo numeric IDs via `gh api` rather than hardcoding them:
  - `github-actions-main` — `subject`: `repo:OWNER@ownerID/REPO@repoID:ref:refs/heads/main` (covers `push`-triggered runs: `terraform-apply.yml`, `backend-deploy.yml`, `frontend-deploy.yml`, `infrastructure-tests.yml`)
  - `github-actions-pull-request` — `subject`: `repo:OWNER@ownerID/REPO@repoID:pull_request` (covers `pull_request`-triggered runs: `terraform-validate.yml`'s Azure-login `terraform plan` step). Discovered during implementation via `AADSTS700213` ("no matching federated identity record") on the first PR-triggered run — a PR's OIDC subject is never `ref:refs/heads/main`, regardless of target branch
  - `issuer` (both): GitHub OIDC issuer (`https://token.actions.githubusercontent.com`)
  - `audience` (both): GitHub Actions default audience (`api://AzureADTokenExchange`)

**Validation Rules**:
- Trust is scoped to specific repository and branch/event (prevents impersonation from forks)
- Federated credentials are configured on the Managed Identity, not a traditional Microsoft Entra App Registration/service principal
- No long-lived credentials stored in GitHub
- Created outside of the main Terraform apply (bootstrap step, alongside the Terraform backend storage account) since Terraform itself authenticates as this identity — a chicken-and-egg constraint identical to the state-storage bootstrap

---

#### Log Analytics Workspace
**Purpose**: Backing workspace for workspace-based Application Insights (the modern, recommended mode) — required for Application Insights to exist at all.

**Properties**:
- `name`: `{prefix}-logs-{env}`
- `sku`: `PerGB2018`
- `retention_in_days`: `30` (confirmed)

**Validation Rules**:
- Must be created before the workspace-based Application Insights resource
- Application Insights' `workspace_id` references this resource

---

#### Application Insights
**Purpose**: Observability and telemetry sink for application logs, metrics, and LLM interaction data. Workspace-based, backed by the Log Analytics Workspace above.

**Properties**:
- `name`: `{prefix}-appinsights-{env}`
- `application_type`: `web`
- `workspace_id`: References the [Log Analytics Workspace](#log-analytics-workspace)
- `retention_in_days`: `30` (matches the Log Analytics Workspace retention, confirmed)
- `daily_quota_gb`: `5` (auto-throttle after 5 GB/day; can be adjusted)

**Telemetry Collection**:
- Application logs (Python backend via OpenTelemetry SDK)
- Request/response metrics (latency, status codes)
- LLM interaction traces (prompts, responses, tokens, cost)
- Error traces and exceptions
- Custom events (game state, player actions)

**Validation Rules**:
- Functions app linked to Application Insights (connection string in app settings)
- OpenTelemetry SDK configured in Python backend
- Telemetry queryable for cost analysis and performance debugging

---

#### Budget & Cost Alert
**Purpose**: Early warning if spend on the `llm-dungeon` Resource Group exceeds an expected threshold (AI Foundry token usage, Cosmos DB, Storage, etc.).

**Properties**:
- `resource_type`: `azurerm_consumption_budget_resource_group`
- `scope`: The `llm-dungeon` Resource Group
- `amount`: `50` (USD/month, confirmed)
- `notification_threshold`: `80%` and `100%` of budget, email alert

**Validation Rules**:
- Budget is scoped to the Resource Group, not the whole subscription (other projects, if any, aren't included)
- At least one contact email configured to receive threshold notifications

---

## Relationships & Dependencies

**Flow Diagram**:
```
GitHub Actions (CI/CD)
  ↓
  ├→ terraform validate/plan/apply
  │   ↓
  │   Creates/Updates Azure Resources
  │       ├→ Storage Account (state + assets)
  │       ├→ Cosmos DB (story data)
  │       ├→ Azure Functions (backend)
  │       ├→ Azure Static Web App (frontend)
  │       ├→ Azure AI Foundry (LLM)
  │       ├→ Managed Identity (auth)
  │       ├→ Private Endpoints (networking)
  │       ├→ Private DNS Zones (DNS)
  │       └→ Application Insights (observability)
  │
  ├→ backend-deploy.yml (build & deploy Python Functions)
  │   ↓
  │   Functions pulls dependencies, registers with Managed Identity
  │   ↓
  │   Functions calls Storage, Cosmos, AI Foundry via private endpoints
  │
  └→ frontend-deploy.yml (build & deploy Static Web App)
      ↓
      Static Web App served globally
      ↓
      Client MSAL login → Entra ID
      ↓
      Client calls Functions (public HTTPS) → Entra ID auth
```

**Trust Boundaries**:
1. **GitHub ↔ Azure**: Federated OIDC bound to the dedicated GitHub OIDC Managed Identity (no stored credentials, no app registration)
2. **Functions ↔ Storage/Cosmos/AI**: Managed Identity (no keys/connection strings)
3. **Client ↔ Functions**: Entra ID bearer token (HTTPS only)
4. **Functions ↔ Services**: Private endpoints (no public internet traversal)

---

## Validation Checklist

- [ ] All Terraform resources defined in configuration
- [ ] Managed Identity roles assigned to correct scopes (Function App identity and GitHub OIDC identity kept separate)
- [ ] Private endpoints created for Storage, Cosmos, AI Foundry
- [ ] Private DNS zones linked to Functions VNet
- [ ] Public network access disabled on all backend resources (Storage, Cosmos, AI)
- [ ] Application settings contain all required environment variables
- [ ] GitHub federated OIDC trust configured and scoped to main branch
- [ ] GitHub environment variables match Terraform outputs
- [ ] Application Insights linked to Functions app
