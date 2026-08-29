# Deployment Configuration Contract

**Date**: 2026-08-28 | **Status**: Phase 1

This contract defines the configuration schema for application settings, environment variables, and deployment parameters.

## Azure Functions Application Settings

**Location**: Azure Portal → Functions App → Settings → Application Settings (or via Terraform `app_settings` block)

**Injected by Terraform** (from Terraform outputs):

These are set by Terraform configuration and should not be manually edited (they will be overwritten on next `terraform apply`).

```
COSMOS_ENDPOINT=https://llmdungeon-cosmos-prod.documents.azure.com:443/
COSMOS_DATABASE=llmdungeon-db-prod
COSMOS_CONTAINER=stories

STORAGE_ACCOUNT_URL=https://llmdungeonassetsprod.blob.core.windows.net/
STORAGE_CONTAINER=assets

AZURE_OPENAI_ENDPOINT=https://llmdungeon-openai-prod.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxxxx;IngestionEndpoint=https://xxx.in.applicationinsights.azure.com/;LiveEndpoint=https://xxx.livediagnostics.monitor.azure.com/

PYTHON_ENABLE_WORKER_EXTENSIONS=true
```

**Validation Rules**:
- All endpoints must be resolvable and reachable from Functions runtime (via private endpoints)
- Cosmos and Storage endpoints must include trailing slashes
- Azure OpenAI endpoint must be the private endpoint URL (not public)
- Application Insights connection string must be non-empty (telemetry enabled)
- Python worker extensions enabled for OpenTelemetry support

---

## GitHub Environment Variables

**Location**: GitHub Settings → Secrets and variables → Actions → **Variables** (repository level, not scoped to either the `production` or `production-infra` environment — both environments' workflows read the same values, and none are secrets)

**Public variables** (visible in workflow logs, not secrets):

```
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
RESOURCE_GROUP_NAME=llm-dungeon
FUNCTIONS_APP_NAME=llmdungeon-func-prod
STORAGE_ACCOUNT_NAME=llmdungeonassetsprod
COSMOS_ACCOUNT_NAME=llmdungeon-cosmos-prod
STATIC_WEB_APP_NAME=llmdungeon-web-prod
AZURE_OPENAI_ACCOUNT_NAME=llmdungeon-openai-prod
TERRAFORM_VERSION=1.16.0
AZURE_PROVIDER_VERSION=3.80.0
```

**No Secrets Stored** (per Principle VII - Zero-Trust):
- No Azure subscription keys
- No Azure connection strings
- No storage account access keys
- No Cosmos DB connection strings
- No OpenAI API keys
- No credentials of any kind

All authentication via federated OIDC (GitHub → Azure identity exchange).

**Validation Rules**:
- No sensitive values in environment variables
- All resource names match Terraform outputs
- Version variables match those used in Terraform CI/CD workflows

---

## Backend Configuration File (backend-prod.hcl)

**Location**: `terraform/backend-prod.hcl` (checked into Git, public)

**Purpose**: Terraform backend configuration (remote state storage)

**Schema**:
```hcl
resource_group_name  = "string"  # Pre-existing Azure Resource Group name (not created by Terraform)
storage_account_name = "string"  # Storage account name (created during bootstrap)
container_name       = "string"  # Container name (default: "terraform-state")
key                  = "string"  # Blob key/path (default: "{environment}.tfstate")
```

**Example (Production)**:
```hcl
resource_group_name  = "llm-dungeon"    # Pre-existing; all project resources (app + Terraform state) live here
storage_account_name = "llmdungeontstateprod"
container_name       = "terraform-state"
key                  = "production.tfstate"
```

**Usage**:
```bash
terraform init -backend-config=backend-prod.hcl
```

**Validation Rules**:
- Storage account must be created during bootstrap (before main Terraform runs)
- Storage account name must be 3-24 characters, lowercase alphanumeric only (Azure constraint)
- Container must exist in the storage account
- No authentication credentials in this file (Azure CLI context or OIDC used for auth)

---

## Terraform Variables File (terraform.tfvars)

**Location**: `terraform/terraform.tfvars` (checked into Git, public, no secrets)

**Purpose**: Environment-specific input values for Terraform

**Schema**:
```hcl
# Core environment
environment          = "string"  # "production", "staging", etc.
azure_region         = "string"  # Azure region for all resources except Cosmos DB (e.g., "westeurope", "westus2")
cosmos_region        = "string"  # Azure region for Cosmos DB specifically — westeurope is out of capacity (research.md §9); "uksouth"
resource_prefix      = "string"  # Resource name prefix (3-10 chars)
resource_group_name  = "string"  # Pre-existing Resource Group (not created by Terraform)
minimum_tls_version  = "string"  # "1.2"

# Common tags
tags = {
  environment = "string"  # e.g., "production"
  managed_by  = "string"  # "terraform"
  project     = "string"  # "llm-dungeon"
  application = "string"  # "llm-dungeon"
  owner       = "string"  # responsible team/person
}

# Backend configuration (matches backend-prod.hcl)
terraform_backend_storage_account = "string"  # Storage account name
terraform_backend_container       = "string"  # Container name
terraform_backend_key             = "string"  # State file key

# Networking
vnet_address_space               = list(string)  # ["10.0.0.0/16"]
functions_subnet_prefix          = "string"       # "10.0.1.0/24"
private_endpoints_subnet_prefix  = "string"       # "10.0.2.0/24"

# Resource-specific configuration
functions_python_version       = "string"  # "3.11"
functions_hosting_plan          = "string"  # "FC1" (Flex Consumption)
cosmos_consistency_level       = "string"  # "Session"
cosmos_max_throughput          = number   # 40000 (serverless max)
cosmos_backup_type              = "string"  # "Periodic"
storage_account_replication    = "string"  # "LRS"
ai_foundry_model_name           = "string"  # "gpt-4o-mini"
ai_foundry_capacity             = number   # 1 (= 1,000 TPM)
log_analytics_retention_days    = number   # 30
budget_amount_usd               = number   # 50
budget_alert_email              = "string"  # notification recipient

# GitHub configuration
github_repository_owner   = "string"  # GitHub org/user
github_repository_name    = "string"  # Repository name
github_repository_branch  = "string"  # "main"
```

**Example (Production)**:
```hcl
environment          = "production"
azure_region         = "westeurope"
cosmos_region        = "uksouth"
resource_prefix      = "llmdungeon"
resource_group_name  = "llm-dungeon"
minimum_tls_version  = "1.2"

tags = {
  environment = "production"
  managed_by  = "terraform"
  project     = "llm-dungeon"
  application = "llm-dungeon"
  owner       = "Reza Mahmood"
}

terraform_backend_storage_account = "llmdungeontstateprod"
terraform_backend_container       = "terraform-state"
terraform_backend_key             = "production.tfstate"

vnet_address_space              = ["10.0.0.0/16"]
functions_subnet_prefix         = "10.0.1.0/24"
private_endpoints_subnet_prefix = "10.0.2.0/24"

functions_python_version    = "3.11"
functions_hosting_plan       = "FC1"
cosmos_consistency_level    = "Session"
cosmos_max_throughput       = 40000
cosmos_backup_type           = "Periodic"
storage_account_replication = "LRS"
ai_foundry_model_name        = "gpt-4o-mini"
ai_foundry_capacity          = 1
log_analytics_retention_days = 30
budget_amount_usd            = 50
budget_alert_email           = "reza.mahmood@gmail.com"

github_repository_owner  = "RezaMahmood"
github_repository_name   = "llm-dungeon"
github_repository_branch = "main"
```

**Validation Rules**:
- `environment`: Must be one of: ["production", "staging", "development"]
- `azure_region`: Must be valid Azure region code (e.g., "westeurope", "westus2", "northeurope")
- `resource_prefix`: 3-10 characters, alphanumeric only, lowercase
- `resource_group_name`: Must reference a Resource Group that already exists
- `tags`: Object with at least `environment`, `managed_by`, `project`, `application`, `owner` keys
- Backend values must match bootstrap-created storage account details
- GitHub repository details must match actual repository

---

## Bootstrap Procedure

**Prerequisites**: Azure CLI configured with subscription access

**Step 1: Create Bootstrap Storage Account**
```bash
#!/bin/bash
set -e

SUBSCRIPTION_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
RESOURCE_GROUP="llm-dungeon"  # Pre-existing — all project resources (Terraform state, app resources) live in this one group
STORAGE_ACCOUNT="llmdungeontstateprod"  # 3-24 chars, lowercase alphanumeric
CONTAINER_NAME="terraform-state"
REGION="westeurope"

# Log in to Azure
az login --use-device-code

# Set subscription
az account set --subscription "$SUBSCRIPTION_ID"

# Verify the pre-existing resource group exists (Terraform never creates or deletes it)
az group show --name "$RESOURCE_GROUP" >/dev/null || {
  echo "✗ Resource Group '$RESOURCE_GROUP' does not exist. It must be created out-of-band before bootstrap." >&2
  exit 1
}

# Create storage account (for Terraform state) inside the pre-existing resource group.
# default-action stays "Allow": this account is created before any VNet exists,
# so GitHub-hosted runners and developer machines (neither on a private path to
# it) must be able to reach it. Access is still Azure-AD-gated (--auth-mode
# login below, use_azuread_auth in backend.tf), never anonymous or key-based.
az storage account create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$STORAGE_ACCOUNT" \
  --location "$REGION" \
  --sku "Standard_LRS" \
  --access-tier "Hot" \
  --https-only true

# Create container
az storage container create \
  --account-name "$STORAGE_ACCOUNT" \
  --name "$CONTAINER_NAME" \
  --auth-mode login

# Enable versioning (for state backup)
az storage account blob-service-properties update \
  --account-name "$STORAGE_ACCOUNT" \
  --enable-versioning true

echo "✓ Bootstrap storage account created: $STORAGE_ACCOUNT"
echo "✓ Container created: $CONTAINER_NAME"
echo "✓ Update terraform/backend-prod.hcl and terraform/terraform.tfvars with:"
echo "  - resource_group_name: $RESOURCE_GROUP"
echo "  - storage_account_name: $STORAGE_ACCOUNT"
```

**Step 2: Create GitHub OIDC Managed Identity and Configure Federated Trust**

(Dedicated user-assigned Managed Identity — separate from the Functions app's runtime Managed Identity — scoped only to the role assignments deployment/Terraform-apply workflows need.)

```bash
#!/bin/bash
set -e

GITHUB_ORG="RezaMahmood"
GITHUB_REPO="llm-dungeon"
TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
RESOURCE_GROUP="llm-dungeon"
REGION="westeurope"
IDENTITY_NAME="llmdungeon-github-oidc-identity-prod"

# This org/repo issues OIDC subject claims in the newer immutable-ID format
# ("repo:OWNER@ownerID/REPO@repoID:...") rather than the classic name-only
# format — fetch the IDs dynamically rather than hardcoding them.
GITHUB_OWNER_ID=$(gh api "users/$GITHUB_ORG" --jq '.id')
GITHUB_REPO_ID=$(gh api "repos/$GITHUB_ORG/$GITHUB_REPO" --jq '.id')
GITHUB_SUBJECT_PREFIX="repo:${GITHUB_ORG}@${GITHUB_OWNER_ID}/${GITHUB_REPO}@${GITHUB_REPO_ID}"

# Create the dedicated user-assigned Managed Identity for GitHub Actions
az identity create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$IDENTITY_NAME" \
  --location "$REGION"

IDENTITY_CLIENT_ID=$(az identity show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$IDENTITY_NAME" \
  --query clientId -o tsv)

IDENTITY_PRINCIPAL_ID=$(az identity show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$IDENTITY_NAME" \
  --query principalId -o tsv)

# Grant only the role assignments the deployment/Terraform-apply workflows need
# (e.g., Contributor scoped to the resource group, not the subscription)
az role assignment create \
  --assignee-object-id "$IDENTITY_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

# Storage Blob Data Contributor on the state Storage Account: Contributor
# (above) is an ARM control-plane role only — it does not grant blob
# data-plane access needed for `terraform init`/`plan`/`apply` to read/write
# the state blob under backend.tf's use_azuread_auth = true. Grant this to
# both the identity and the human running bootstrap.
az role assignment create \
  --assignee-object-id "$IDENTITY_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

CURRENT_USER_OID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create \
  --assignee-object-id "$CURRENT_USER_OID" \
  --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

# Four federated credentials, not one — GitHub's OIDC subject claim shape
# depends on trigger AND whether the job sets `environment:` (which overrides
# the branch/event-based subject entirely). Every workflow here that calls
# azure/login also sets `environment:`, so each needed its own credential —
# discovered one AADSTS700213 at a time by actually running the workflows.
declare -A FEDERATED_CREDENTIALS=(
  ["github-actions-main"]="ref:refs/heads/main"                       # unused today; kept for future push-triggered jobs with no environment:
  ["github-actions-pull-request"]="pull_request"                      # terraform-validate.yml's `terraform plan` step on PRs
  ["github-actions-env-production"]="environment:production"          # backend-deploy.yml, frontend-deploy.yml, infrastructure-tests.yml
  ["github-actions-env-production-infra"]="environment:production-infra"  # terraform-apply.yml
)
for cred_name in "${!FEDERATED_CREDENTIALS[@]}"; do
  az identity federated-credential create \
    --name "$cred_name" \
    --identity-name "$IDENTITY_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --issuer "https://token.actions.githubusercontent.com" \
    --subject "${GITHUB_SUBJECT_PREFIX}:${FEDERATED_CREDENTIALS[$cred_name]}" \
    --audiences "api://AzureADTokenExchange"
done

echo "✓ Federated OIDC trust configured on Managed Identity: $IDENTITY_NAME"
echo "✓ Use these values in GitHub environment variables:"
echo "  - AZURE_TENANT_ID: $TENANT_ID"
echo "  - AZURE_CLIENT_ID: $IDENTITY_CLIENT_ID"
echo "  - AZURE_SUBSCRIPTION_ID: <subscription-id>"
```

**Step 3: Set GitHub Repository Variables**

Go to: GitHub repo Settings → Secrets and variables → Actions → Variables tab → New repository variable (repo-level, shared by both the `production` and `production-infra` environments)

```
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
RESOURCE_GROUP_NAME=llm-dungeon
FUNCTIONS_APP_NAME=llmdungeon-func-prod
STORAGE_ACCOUNT_NAME=llmdungeonassetsprod
COSMOS_ACCOUNT_NAME=llmdungeon-cosmos-prod
STATIC_WEB_APP_NAME=llmdungeon-web-prod
TERRAFORM_VERSION=1.16.0
AZURE_PROVIDER_VERSION=3.80.0
```

**Step 4: Run Terraform**

```bash
cd terraform/

# Initialize with backend
terraform init -backend-config=backend-prod.hcl

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# Export outputs
terraform output -json > outputs.json
```

**Validation**: 
- Storage account created and accessible
- GitHub OIDC Managed Identity created with federated credential and scoped role assignment
- GitHub environment variables set
- Terraform initialization succeeds
- Terraform plan shows expected resources

---

## Configuration Hierarchy

**Priority Order** (highest to lowest):
1. Environment variables (GitHub Actions, local terminal)
2. Terraform variables file (`terraform.tfvars`)
3. Terraform variable defaults (in `variables.tf`)
4. Application settings (Functions app)

**Example**: If `COSMOS_ENDPOINT` is set both in GitHub environment and in Function App settings, the Function App setting takes precedence at runtime.

---

## Secrets Management

**No Secrets Stored** (per Principle VII):
- GitHub Secrets: Empty (no Azure credentials stored)
- Terraform state: Contains no sensitive values (no hardcoded keys, connection strings, or API keys)
- Application code: No hardcoded credentials

**Authentication Mechanisms**:
1. **GitHub → Azure**: Federated OIDC bound to a dedicated GitHub OIDC Managed Identity (no credentials needed, no app registration)
2. **Functions → Azure Services**: Managed Identity (no credentials needed)
3. **Developer → Azure**: Azure CLI (local auth, not checked into Git)

**Audit Trail**:
- Terraform state file: Versioned in Azure Storage (state locking prevents concurrent corruption)
- GitHub Actions logs: Record all deployments (available in repo Actions tab)
- Azure Activity Log: Record all resource changes (in Azure Portal)

---

## Validation & Error Handling

**Pre-Deployment Validation**:
- Terraform validate/fmt check (in PR workflows)
- Application settings presence check (Functions app startup)
- Connectivity validation (infrastructure-tests.yml)

**Runtime Validation**:
- Functions startup: Assert all required application settings present
- Cosmos connection: Attempt connection during initialization; fail-fast if unreachable
- Storage connection: Test blob access on first request; clear error if Managed Identity lacks permissions
- Azure OpenAI connection: Validate endpoint and model deployment exist

**Error Scenarios**:
- Missing application setting → Functions logs clear error; pod exits with status 1
- Managed Identity lacks role → Access denied error with role name (e.g., "Storage Blob Data Contributor required")
- Private endpoint misconfigured → Connection timeout; network trace shows connection attempts to wrong IP
- OIDC authentication fails → Azure login action returns "invalid_client" or similar (check federated credential configuration)

**Recovery**:
- Configuration error: Update setting/variable, re-run Terraform or redeply Functions app
- Permission error: Add missing role assignment via Azure Portal or Terraform
- Network error: Check private endpoint configuration, DNS resolution, and network rules
