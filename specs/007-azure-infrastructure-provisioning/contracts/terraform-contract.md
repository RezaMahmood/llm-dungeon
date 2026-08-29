# Terraform Configuration Contract

**Date**: 2026-08-28 | **Status**: Phase 1

This contract defines the Terraform variables (inputs) and outputs that infrastructure code must provide.

## Input Variables (terraform/variables.tf)

All variables are defined in `terraform/variables.tf`. Configuration-specific values are provided in `terraform.tfvars` (Production).

### Core Environment Variables

```hcl
variable "environment" {
  description = "Deployment environment (e.g., production, staging)"
  type        = string
  # Value in terraform.tfvars: "production"
}

variable "azure_region" {
  description = "Azure region for all resources except Cosmos DB (see cosmos_region)"
  type        = string
  default     = "westeurope"  # Confirmed
}

variable "cosmos_region" {
  description = "Azure region for the Cosmos DB account specifically. Separate from azure_region: westeurope is confirmed out of Cosmos DB capacity (research.md §9). Private Link works cross-region, so no other resource needs to move."
  type        = string
  default     = "uksouth"
}

variable "resource_prefix" {
  description = "Prefix for all resource names (e.g., 'llmdungeon')"
  type        = string
  # Value in terraform.tfvars: "llmdungeon"
}

variable "resource_group_name" {
  description = "Name of the pre-existing Azure Resource Group that all resources for this project are provisioned into. This Resource Group is NOT created by Terraform — it is created out-of-band before any Terraform run and referenced here as a data source."
  type        = string
  default     = "llm-dungeon"
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    managed_by  = "terraform"
    project     = "llm-dungeon"
    application = "llm-dungeon"
    environment = "production"
    owner       = "Reza Mahmood"
  }
}

variable "minimum_tls_version" {
  description = "Minimum TLS version enforced on Storage, Cosmos DB, and Functions"
  type        = string
  default     = "1.2"
}
```

### Azure Subscription Variables

```hcl
variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
  # Value from GitHub environment variable
}

variable "azure_tenant_id" {
  description = "Azure Entra ID tenant ID"
  type        = string
  sensitive   = true
  # Value from GitHub environment variable
}

variable "azure_client_id" {
  description = "GitHub OIDC Managed Identity client ID (dedicated user-assigned Managed Identity carrying the federated credential for GitHub Actions; not a service principal/app registration)"
  type        = string
  sensitive   = true
  # Value from GitHub environment variable
}
```

### Terraform Backend Variables

```hcl
variable "terraform_backend_storage_account" {
  description = "Storage account name for Terraform remote state"
  type        = string
  # Value in terraform.tfvars: storage account created during bootstrap
}

variable "terraform_backend_container" {
  description = "Container name in backend storage account"
  type        = string
  default     = "terraform-state"
}

variable "terraform_backend_key" {
  description = "Blob key (file path) for state file"
  type        = string
  # Value in terraform.tfvars: "{environment}.tfstate"
}
```

### Resource-Specific Variables

```hcl
variable "functions_python_version" {
  description = "Python version for Azure Functions"
  type        = string
  default     = "3.11"
}

variable "cosmos_consistency_level" {
  description = "Cosmos DB consistency level"
  type        = string
  default     = "Session"
  # Values: Strong, BoundedStaleness, Session, ConsistentPrefix, Eventual
}

variable "cosmos_max_throughput" {
  description = "Maximum RU/s for serverless Cosmos DB auto-scaling"
  type        = number
  default     = 40000
}

variable "cosmos_backup_type" {
  description = "Cosmos DB backup policy type"
  type        = string
  default     = "Periodic"
  # Values: Periodic, Continuous
}

variable "storage_account_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "LRS"
  # Values: LRS, GRS, RAGRS, ZRS
}

variable "vnet_address_space" {
  description = "Address space for the project Virtual Network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "functions_subnet_prefix" {
  description = "CIDR for the Functions VNet-integration subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_endpoints_subnet_prefix" {
  description = "CIDR for the private-endpoints subnet (Storage, Cosmos DB, AI Foundry)"
  type        = string
  default     = "10.0.2.0/24"
}

variable "functions_hosting_plan" {
  description = "Azure Functions hosting plan SKU"
  type        = string
  default     = "FC1"  # Flex Consumption
}

variable "ai_foundry_model_name" {
  description = "Model to deploy to Azure AI Foundry / Azure OpenAI"
  type        = string
  default     = "gpt-4o-mini"
}

variable "ai_foundry_capacity" {
  description = "Deployment capacity in Terraform capacity units (1 unit = 1,000 TPM)"
  type        = number
  default     = 1  # 1,000 TPM / 1K TPM
}

variable "log_analytics_retention_days" {
  description = "Log Analytics Workspace retention period, backing Application Insights"
  type        = number
  default     = 30
}

variable "budget_amount_usd" {
  description = "Monthly budget amount (USD) for the Resource Group cost alert"
  type        = number
  default     = 50
}

variable "budget_alert_email" {
  description = "Email address to notify at 80%% and 100%% of the monthly budget"
  type        = string
  # Value in terraform.tfvars
}

variable "github_repository_owner" {
  description = "GitHub repository owner (org or user)"
  type        = string
  # Value in terraform.tfvars
}

variable "github_repository_name" {
  description = "GitHub repository name"
  type        = string
  # Value in terraform.tfvars
}

variable "github_repository_branch" {
  description = "GitHub branch for Static Web App auto-deploy"
  type        = string
  default     = "main"
}
```

---

## Output Values (terraform/outputs.tf)

Outputs are exported for GitHub Actions workflows and downstream consumption. All outputs are defined in `terraform/outputs.tf`.

### Infrastructure Resource Names & IDs

All resources are provisioned into the single, pre-existing `llm-dungeon` Resource Group, referenced via a data source (not created by this configuration):

```hcl
data "azurerm_resource_group" "rg" {
  name = var.resource_group_name  # "llm-dungeon" — pre-existing, not managed by Terraform
}
```

```hcl
output "resource_group_name" {
  value       = data.azurerm_resource_group.rg.name
  description = "Azure Resource Group name (pre-existing 'llm-dungeon' group; all project resources are provisioned into it)"
}

output "resource_group_id" {
  value       = data.azurerm_resource_group.rg.id
  description = "Azure Resource Group ID"
}

output "functions_app_name" {
  value       = azurerm_linux_function_app.functions.name
  description = "Azure Functions app name"
}

output "functions_app_id" {
  value       = azurerm_linux_function_app.functions.id
  description = "Azure Functions app resource ID"
}

output "functions_managed_identity_principal_id" {
  value       = azurerm_linux_function_app.functions.identity[0].principal_id
  description = "Managed Identity principal ID for role assignments"
}

output "static_web_app_name" {
  value       = azurerm_static_web_app.web.name
  description = "Azure Static Web App name"
}

output "static_web_app_id" {
  value       = azurerm_static_web_app.web.id
  description = "Azure Static Web App resource ID"
}

output "static_web_app_url" {
  value       = azurerm_static_web_app.web.default_host_name
  description = "Static Web App default hostname (e.g., xxx.azurestaticapps.net)"
}

output "storage_account_name" {
  value       = azurerm_storage_account.app_storage.name
  description = "Application storage account name"
}

output "storage_account_id" {
  value       = azurerm_storage_account.app_storage.id
  description = "Application storage account resource ID"
}

output "storage_blob_endpoint" {
  value       = azurerm_storage_account.app_storage.primary_blob_endpoint
  description = "Storage account Blob Service endpoint (public; private endpoint used by Functions)"
}

output "storage_private_endpoint_ip" {
  value       = azurerm_private_endpoint.storage_pe.private_service_connection[0].private_ip_address
  description = "Private IP of Storage account private endpoint"
}

output "cosmos_db_account_name" {
  value       = azurerm_cosmosdb_account.cosmos.name
  description = "Cosmos DB account name"
}

output "cosmos_db_id" {
  value       = azurerm_cosmosdb_account.cosmos.id
  description = "Cosmos DB account resource ID"
}

output "cosmos_endpoint" {
  value       = azurerm_cosmosdb_account.cosmos.endpoint
  description = "Cosmos DB account endpoint URL (public; private endpoint used by Functions)"
}

output "cosmos_private_endpoint_ip" {
  value       = azurerm_private_endpoint.cosmos_pe.private_service_connection[0].private_ip_address
  description = "Private IP of Cosmos DB private endpoint"
}

output "cosmos_database_name" {
  value       = azurerm_cosmosdb_sql_database.db.name
  description = "Cosmos DB database name"
}

output "cosmos_container_name" {
  value       = azurerm_cosmosdb_sql_container.stories.name
  description = "Cosmos DB stories container name"
}

output "azure_openai_account_name" {
  value       = azurerm_cognitive_account.openai.name
  description = "Azure OpenAI Service account name"
}

output "azure_openai_id" {
  value       = azurerm_cognitive_account.openai.id
  description = "Azure OpenAI Service resource ID"
}

output "azure_openai_endpoint" {
  value       = azurerm_cognitive_account.openai.endpoint
  description = "Azure OpenAI Service endpoint URL (public; private endpoint used by Functions)"
}

output "azure_openai_deployment_name" {
  value       = azurerm_cognitive_deployment.model.name
  description = "Model deployment name (e.g., 'gpt-4o-mini')"
}

output "application_insights_id" {
  value       = azurerm_application_insights.appinsights.id
  description = "Application Insights resource ID"
}

output "application_insights_connection_string" {
  value       = azurerm_application_insights.appinsights.connection_string
  description = "Application Insights connection string (for Functions app settings)"
  sensitive   = true
}

output "application_insights_instrumentation_key" {
  value       = azurerm_application_insights.appinsights.instrumentation_key
  description = "Application Insights instrumentation key"
  sensitive   = true
}

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.logs.id
  description = "Log Analytics Workspace ID (backs Application Insights)"
}
```

### Networking & DNS

```hcl
output "vnet_id" {
  value       = azurerm_virtual_network.vnet.id
  description = "Virtual Network resource ID"
}

output "functions_subnet_id" {
  value       = azurerm_subnet.functions.id
  description = "Functions VNet-integration subnet ID"
}

output "private_endpoints_subnet_id" {
  value       = azurerm_subnet.private_endpoints.id
  description = "Private endpoints subnet ID"
}

output "private_dns_zone_blob" {
  value       = azurerm_private_dns_zone.blob.name
  description = "Private DNS zone for Blob Storage (privatelink.blob.core.windows.net)"
}

output "private_dns_zone_cosmos" {
  value       = azurerm_private_dns_zone.cosmos.name
  description = "Private DNS zone for Cosmos DB (privatelink.documents.azure.com)"
}

output "private_dns_zone_openai" {
  value       = azurerm_private_dns_zone.openai.name
  description = "Private DNS zone for Azure OpenAI (privatelink.openai.azure.com)"
}
```

### Cost Management

```hcl
output "budget_name" {
  value       = azurerm_consumption_budget_resource_group.budget.name
  description = "Name of the Resource Group budget/cost alert"
}
```

### GitHub Actions Integration

```hcl
output "github_environment_variables" {
  value = {
    RESOURCE_GROUP_NAME = data.azurerm_resource_group.rg.name
    FUNCTIONS_APP_NAME  = azurerm_linux_function_app.functions.name
    STORAGE_ACCOUNT_NAME = azurerm_storage_account.app_storage.name
    COSMOS_ACCOUNT_NAME  = azurerm_cosmosdb_account.cosmos.name
    STATIC_WEB_APP_NAME  = azurerm_static_web_app.web.name
    AZURE_OPENAI_ENDPOINT = azurerm_cognitive_account.openai.endpoint
    AZURE_OPENAI_DEPLOYMENT_NAME = azurerm_cognitive_deployment.model.name
  }
  description = "Environment variables for GitHub Actions (public, not secrets)"
}
```

---

## Backend Configuration File (backend-prod.hcl)

```hcl
# backend-prod.hcl
# Passed to: terraform init -backend-config=backend-prod.hcl

resource_group_name  = "llm-dungeon"     # Pre-existing Resource Group, not created by Terraform
storage_account_name = "llmdungeontstateprod"  # Created during bootstrap
container_name       = "terraform-state"
key                  = "production.tfstate"
```

**Usage**: 
```bash
terraform init -backend-config=backend-prod.hcl
```

---

## Validation & Constraints

**Required Outputs**: All outputs listed above must be present in `terraform/outputs.tf`. Missing outputs will break downstream GitHub Actions workflows.

**State File**: `terraform.tfstate` stored in Azure Storage account (backend). Never commit to Git.

**Variable Validation**:
- `environment` must be one of: `["production", "staging", "development"]` (or add validation block)
- `azure_region` must be a valid Azure region string (e.g., "westeurope", "westus2")
- `resource_prefix` must be 3-10 characters, alphanumeric only (for valid Azure resource names)
- `resource_group_name` must reference a Resource Group that already exists (`data.azurerm_resource_group.rg` fails `terraform plan` with a clear error if it does not) — Terraform never creates or deletes this Resource Group
- Sensitive variables (subscription ID, tenant ID, client ID) must be marked `sensitive = true`

**Version Pinning**:
```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.80.0"
    }
  }
}
```
