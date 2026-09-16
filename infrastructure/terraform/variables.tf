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

variable "functions_always_ready_instance_count" {
  description = "Instances kept warm for the Functions app's HTTP trigger group during the warm windows in functions-always-ready-schedule.yml; 0 disables always-ready entirely"
  type        = number
  default     = 1

  validation {
    condition     = var.functions_always_ready_instance_count >= 0 && floor(var.functions_always_ready_instance_count) == var.functions_always_ready_instance_count
    error_message = "functions_always_ready_instance_count must be a whole number of zero or greater."
  }
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

variable "cosmos_allowed_ip_addresses" {
  description = <<-EOT
    Developer IPv4 addresses allowed to reach the Cosmos DB public data plane
    (Data Explorer, a local script). Empty — the default — keeps public network
    access disabled entirely, leaving Private Link as the only path; any entry
    enables the public data plane restricted to exactly these addresses.

    This is a convenience hole in the Principle VII posture, not part of how the
    application reaches Cosmos: the Function App always goes over the private
    endpoint, and nothing here widens that. Keep the list to specific /32
    addresses and remove entries once they are no longer needed. A residential IP
    is typically dynamic, so an entry will silently stop matching when the ISP
    reassigns it — that reads as a 403 from Cosmos, not as a broken deployment.

    Do NOT set this in terraform.tfvars: this repository is public and these are
    personal addresses. It is supplied at plan time from the
    COSMOS_ALLOWED_IP_ADDRESSES GitHub secret, as HCL list syntax, e.g. ["1.2.3.4"].

    infrastructure/tests/test_resource_creation.py asserts at most a single IP rule
    when public access is on, so adding a second address needs that test updated
    alongside it — deliberately, so widening this is never incidental.
  EOT
  type        = list(string)
  default     = []

  validation {
    # Each octet must be 0-255, so a typo like 999.1.1.1 fails here rather than at
    # apply time, and a CIDR suffix or range is rejected outright: "allow my /24" is
    # exactly the accident this should not make easy.
    condition = alltrue([
      for ip in var.cosmos_allowed_ip_addresses :
      can(regex("^((25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)\\.){3}(25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)$", ip))
    ])
    error_message = "cosmos_allowed_ip_addresses must contain bare IPv4 addresses only, each octet 0-255 (no CIDR suffix, no ranges)."
  }

  validation {
    # 0.0.0.0 is not "no address" to Cosmos: it is a documented special case meaning
    # "accept connections from anywhere inside public Azure datacenters" — any VM or
    # Function in any subscription, not just this one. It is a single, well-formed
    # entry, so it would otherwise satisfy both the regex above and the
    # exactly-one-rule assertion in test_resource_creation.py, and slip through as
    # the widest possible opening while looking like the narrowest.
    condition     = !contains(var.cosmos_allowed_ip_addresses, "0.0.0.0")
    error_message = "0.0.0.0 in a Cosmos ip_range_filter means 'allow all Azure datacenter traffic', not a single host. Name real addresses."
  }
}

variable "storage_account_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "LRS"
}

# --- AI Foundry / Azure OpenAI ---

variable "ai_foundry_model_name" {
  description = "Model deployed as the standby/fallback deployment. No longer the deployment the application calls — see ai_foundry_router_deployment_name."
  type        = string
  default     = "gpt-5-nano"
}

variable "ai_foundry_capacity" {
  # 1,000 TPM was too tight even for a single story-creation exchange under
  # light concurrent use, tripping openai.RateLimitError (429) — see #33.
  description = "Capacity for ai_foundry_model_name's deployment, in Terraform capacity units (1 unit = 1,000 TPM). 1000 = 1M TPM."
  type        = number
  default     = 1000
}

variable "ai_foundry_router_deployment_name" {
  description = <<-EOT
    Name of the model-router deployment the Function App calls, via both
    AZURE_OPENAI_DEPLOYMENT_NAME and AZURE_AI_FOUNDRY_DEPLOYMENT_NAME.

    Azure offers model-router on the GlobalStandard SKU only, so inference may be
    served outside the EU data zone. That is a knowing departure from the
    EU-residency posture deployment-questionnaire.md §2 records and from the reason
    gpt-5-nano was pinned to DataZoneStandard — it applies to prompt content in
    flight, not to anything Cosmos stores, which stays in UK South either way.
  EOT
  type        = string
  default     = "model-router"
}

variable "ai_foundry_router_model_version" {
  description = "Pinned model version for the model-router deployment, so Azure's auto-resolved default cannot move it underneath a deploy."
  type        = string
  default     = "2025-11-18"
}

variable "ai_foundry_router_capacity" {
  description = "Capacity for the model-router deployment, in Terraform capacity units (1 unit = 1,000 TPM). 150 = 150K TPM, matching the deployment created out-of-band; raise it if narration starts tripping 429s the way #33 did."
  type        = number
  default     = 150
}

variable "llm_input_token_price_usd" {
  description = "USD price per input token, used to compute gen_ai.cost_usd on every LLM call span (004-story-creation-done, Constitution Principle VI). Default matches gpt-5-nano's published per-token rate as of this writing ($0.05 / 1M input tokens). NOTE: calls now go to model-router, which bills at whichever model it routed to, so a single rate cannot be exact for every call — gen_ai.cost_usd is a floor, not a bill, until this is reworked (see the follow-up on the PR that introduced the router)."
  type        = number
  default     = 0.00000005
}

variable "llm_output_token_price_usd" {
  description = "USD price per output token (004-story-creation-done, Constitution Principle VI). Default matches gpt-5-nano's published per-token rate as of this writing ($0.40 / 1M output tokens). Carries the same model-router caveat as llm_input_token_price_usd above."
  type        = number
  default     = 0.0000004
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
# by the 020-terraform-apply-gating-done quickstart scenarios.

# Scenario 4 (T010) verification run: this pending review is expected to be rejected.

# Scenario 7B trivial passing change (020-terraform-apply-gating-done quick-succession test)
