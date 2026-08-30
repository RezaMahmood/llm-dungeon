variable "environment" {
  description = "Deployment environment (e.g., production, staging)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "environment must be one of: production, staging, development."
  }
}

variable "azure_region" {
  description = "Azure region for all resources"
  type        = string
  default     = "westeurope"
}

variable "cosmos_region" {
  description = "Azure region for the Cosmos DB account specifically — separate from azure_region because westeurope has been confirmed out of Cosmos DB capacity (ServiceUnavailable/'high demand' on every create attempt, including via a direct az cli probe unrelated to Terraform). Every other resource stays in azure_region; only Cosmos DB's data actually lives in this region. Private Link/private endpoints work cross-region, so no other resource needs to move."
  type        = string
  default     = "uksouth"
}

variable "resource_prefix" {
  description = "Prefix for all resource names (e.g., 'llmdungeon')"
  type        = string
  default     = "llmdungeon"

  validation {
    condition     = can(regex("^[a-z0-9]{3,10}$", var.resource_prefix))
    error_message = "resource_prefix must be 3-10 lowercase alphanumeric characters."
  }
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
    owner       = "Reza Mahmood"
  }
}

variable "minimum_tls_version" {
  description = "Minimum TLS version enforced on Storage, Cosmos DB, and Functions"
  type        = string
  default     = "1.2"
}

# --- Azure Subscription / Identity ---

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}

variable "azure_tenant_id" {
  description = "Azure Entra ID tenant ID"
  type        = string
  sensitive   = true
}

variable "azure_client_id" {
  description = "GitHub OIDC Managed Identity client ID (dedicated user-assigned Managed Identity carrying the federated credential for GitHub Actions; not a service principal/app registration)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_app_id" {
  description = "Azure Entra ID App Registration Client ID for Login & Access Control (MSAL frontend authentication)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "seed_admin_email" {
  description = "Email of the initial Administrator account, provisioned on first Function App cold start (003-account-provisioning-done, FR-001). Blank is a no-op."
  type        = string
  default     = ""
}

# --- Terraform Backend (informational only; actual backend config is passed via -backend-config) ---

variable "terraform_backend_storage_account" {
  description = "Storage account name for Terraform remote state (created during bootstrap)"
  type        = string
  default     = ""
}

variable "terraform_backend_container" {
  description = "Container name in backend storage account"
  type        = string
  default     = "terraform-state"
}

variable "terraform_backend_key" {
  description = "Blob key (file path) for state file"
  type        = string
  default     = ""
}

# --- Networking ---

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

# --- Compute ---

variable "functions_python_version" {
  description = "Python version for Azure Functions"
  type        = string
  default     = "3.11"
}

variable "functions_hosting_plan" {
  description = "Azure Functions hosting plan SKU"
  type        = string
  default     = "FC1" # Flex Consumption
}

# --- Data tier ---

variable "cosmos_consistency_level" {
  description = "Cosmos DB consistency level"
  type        = string
  default     = "Session"
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
}

variable "storage_account_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "LRS"
}

# --- AI Foundry / Azure OpenAI ---

variable "ai_foundry_model_name" {
  description = "Model to deploy to Azure AI Foundry / Azure OpenAI"
  type        = string
  default     = "gpt-4o-mini"
}

variable "ai_foundry_capacity" {
  description = "Deployment capacity in Terraform capacity units (1 unit = 1,000 TPM)"
  type        = number
  default     = 1
}

variable "llm_input_token_price_usd" {
  description = "USD price per input token for ai_foundry_model_name's deployed SKU, used to compute gen_ai.cost_usd on every LLM call span (004-story-creation, Constitution Principle VI). Default matches gpt-4o-mini's published per-token rate as of this writing ($0.15 / 1M input tokens) — reverify against the Azure OpenAI pricing page for the deployed region/SKU (DataZoneStandard) before relying on cost telemetry."
  type        = number
  default     = 0.00000015
}

variable "llm_output_token_price_usd" {
  description = "USD price per output token for ai_foundry_model_name's deployed SKU (004-story-creation, Constitution Principle VI). Default matches gpt-4o-mini's published per-token rate as of this writing ($0.60 / 1M output tokens) — reverify against the Azure OpenAI pricing page for the deployed region/SKU (DataZoneStandard) before relying on cost telemetry."
  type        = number
  default     = 0.0000006
}

# --- Observability & Cost ---

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
  description = "Email address to notify at 80% and 100% of the monthly budget"
  type        = string
}

# --- GitHub ---

variable "github_repository_owner" {
  description = "GitHub repository owner (org or user)"
  type        = string
  default     = "RezaMahmood"
}

variable "github_repository_name" {
  description = "GitHub repository name"
  type        = string
  default     = "llm-dungeon"
}

variable "github_repository_branch" {
  description = "GitHub branch for Static Web App auto-deploy"
  type        = string
  default     = "main"
}

# Gate behavior (validate -> test -> apply, manual approval) verified end-to-end
# by the 020-terraform-apply-gating quickstart scenarios.
