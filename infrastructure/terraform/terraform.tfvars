# Environment-specific values (Production). No secrets — see
# contracts/deployment-config-contract.md's Terraform Variables File.
# azure_subscription_id / azure_tenant_id / azure_client_id are supplied at
# apply time via GitHub environment variables (terraform-apply.yml), not here.

environment         = "production"
azure_region        = "westeurope"
resource_prefix     = "llmdungeon"
resource_group_name = "llm-dungeon"
minimum_tls_version = "1.2"

# Cosmos DB only — westeurope is confirmed out of capacity (see main.tf's
# comment on azurerm_cosmosdb_account.cosmos). Every other resource stays in
# azure_region above.
cosmos_region = "uksouth"

tags = {
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

functions_python_version = "3.11"
functions_hosting_plan   = "FC1"

# One warm HTTP instance during functions-always-ready-schedule.yml's windows
# (54h/week): ~$7/month of Always Ready Baseline at 2048 MB against the $50
# budget_amount_usd alert below. That workflow reads this value.
functions_always_ready_instance_count = 1

cosmos_consistency_level         = "Session"
cosmos_max_throughput            = 40000
cosmos_backup_type               = "Periodic"
storage_account_replication_type = "LRS"

# cosmos_allowed_ip_addresses is deliberately NOT set here. This repository is
# public and the value is a maintainer's residential IP; it is supplied at plan time
# from the COSMOS_ALLOWED_IP_ADDRESSES GitHub secret instead (see the TF_VAR_ line in
# terraform-validate.yml and infrastructure-deploy.yml). Unset, it defaults to [],
# which closes the Cosmos public data plane rather than opening it.

# Standby deployment — kept, no longer the one the app calls.
ai_foundry_model_name = "gpt-5-nano"
ai_foundry_capacity   = 1000 # 1M TPM (#33)

# The deployment the Function App actually calls.
ai_foundry_router_deployment_name = "model-router"
ai_foundry_router_model_version   = "2025-11-18"
ai_foundry_router_capacity        = 150 # 150K TPM, as created out-of-band

log_analytics_retention_days = 30
budget_amount_usd            = 50
budget_alert_email           = "reza.mahmood@gmail.com"

github_repository_owner  = "RezaMahmood"
github_repository_name   = "llm-dungeon"
github_repository_branch = "main"
