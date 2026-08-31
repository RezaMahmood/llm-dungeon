# Primary resource definitions (data-model.md's "Terraform Configuration" entity).
# Resources are appended here phase-by-phase per tasks.md (Storage, Cosmos DB,
# AI Foundry, Functions, Static Web App) — see terraform/network.tf,
# terraform/monitoring.tf, and terraform/identity.tf for the rest.

# The `llm-dungeon` Resource Group is pre-existing (created out-of-band) and
# referenced via a data source only — Terraform never creates, modifies, or
# deletes it (data-model.md's Resource Group entity, research.md §8).
data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

# --- Storage Account (Application Assets) ---
# Separate from the Terraform backend state Storage Account (bootstrap-created,
# see backend.tf/infrastructure/scripts/bootstrap.sh). Also hosts the Flex Consumption
# Function App's own deployment package container (app-package), since Flex
# Consumption requires a blob container to deploy from — reusing this account
# avoids introducing a third Storage Account entity beyond the two data-model.md
# defines.
resource "azurerm_storage_account" "app_storage" {
  name                          = local.storage_assets_name
  resource_group_name           = data.azurerm_resource_group.rg.name
  location                      = data.azurerm_resource_group.rg.location
  account_tier                  = "Standard"
  account_replication_type      = var.storage_account_replication_type
  access_tier                   = "Hot"
  https_traffic_only_enabled    = true
  min_tls_version               = "TLS1_2"
  public_network_access_enabled = false
  shared_access_key_enabled     = true # required by Flex Consumption's deployment container access path
  tags                          = local.common_tags
}

resource "azurerm_storage_container" "assets" {
  name                  = "assets"
  storage_account_id    = azurerm_storage_account.app_storage.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "function_deployments" {
  name                  = "app-package"
  storage_account_id    = azurerm_storage_account.app_storage.id
  container_access_type = "private"
}

# --- Cosmos DB (serverless story configuration data) ---
# Deployed to var.cosmos_region (UK South), NOT var.azure_region (West Europe)
# like every other resource here — West Europe is confirmed out of Cosmos DB
# capacity (Azure returns ServiceUnavailable/"high demand" on every create
# attempt, including a direct az cli probe unrelated to this Terraform config).
# Private Link works cross-region, so the VNet/private endpoint stay in West
# Europe; only Cosmos's own data plane lives in UK South.
resource "azurerm_cosmosdb_account" "cosmos" {
  name                = local.cosmos_account_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.cosmos_region
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  public_network_access_enabled = false
  minimal_tls_version           = "Tls12"

  # Single region, single write region, no automatic failover: this project's
  # scale (research.md §3, ~5-10 users) needs neither AZ redundancy nor
  # geo-replication, and multi-region here would just be a second region to
  # keep matching West Europe's capacity constraints against.
  automatic_failover_enabled       = false
  multiple_write_locations_enabled = false

  # True serverless (per-request billing, no manual RU/s tuning) — Principle IV
  # (YAGNI). Databases/containers below intentionally set no throughput or
  # autoscale_settings block: Azure rejects either when EnableServerless is
  # present. cosmos_max_throughput remains defined in variables.tf for
  # contract compatibility but is unused here.
  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = var.cosmos_consistency_level
  }

  backup {
    type = var.cosmos_backup_type
    # Azure now requires these explicit even when they match its own defaults
    # (research.md §3: "every 4h, 7-day retention").
    interval_in_minutes = 240
    retention_in_hours  = 168
  }

  geo_location {
    location          = var.cosmos_region
    failover_priority = 0
    # No Availability Zone redundancy needed at this project's scale, and AZ
    # capacity is exactly what's constrained in West Europe right now anyway.
    zone_redundant = false
  }

  tags = local.common_tags
}

resource "azurerm_cosmosdb_sql_database" "db" {
  name                = local.cosmos_database_name
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
}

resource "azurerm_cosmosdb_sql_container" "stories" {
  name                  = "stories"
  resource_group_name   = data.azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_paths   = ["/id"]
  partition_key_version = 2
}

resource "azurerm_cosmosdb_sql_container" "story_drafts" {
  # 004-story-creation, data-model.md Storage Model: ephemeral in-progress
  # wizard sessions, one document per draft. default_ttl = -1 enables
  # per-item TTL without a container-wide expiry — every StoryDraft document
  # sets its own `ttl` field (reset to 86400 on each update, research.md §3),
  # so nothing expires unless the application says so.
  name                  = "storyDrafts"
  resource_group_name   = data.azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_paths   = ["/id"]
  partition_key_version = 2
  default_ttl           = -1
}

resource "azurerm_cosmosdb_sql_container" "provisioned_account_entries" {
  # Replaces allowListEntries + capabilityAssignments (003-account-provisioning-done):
  # both were keyed by user_oid; this single container is keyed by lowercased
  # email so an entry can be looked up before its first sign-in binds an oid
  # (data-model.md §"Migration Notes"). No production data existed in either
  # superseded container, so this is a schema replacement, not a live migration.
  name                  = "provisionedAccountEntries"
  resource_group_name   = data.azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_paths   = ["/email"]
  partition_key_version = 2

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}

# --- Azure AI Foundry / Azure OpenAI ---
resource "azurerm_cognitive_account" "openai" {
  name                = local.openai_account_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  kind                = "OpenAI"
  sku_name            = "S0"

  custom_subdomain_name         = local.openai_account_name # required for Private Link / private endpoint DNS
  public_network_access_enabled = false

  tags = local.common_tags
}

resource "azurerm_cognitive_deployment" "model" {
  name                 = var.ai_foundry_model_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format = "OpenAI"
    name   = var.ai_foundry_model_name
    # gpt-4o-mini was retired by OpenAI/Azure; replaced with gpt-5-nano
    # (2026-08-31, #33's rate-limit investigation surfaced the deprecation).
    # Pinned to avoid drift against Azure's auto-resolved default.
    version = "2025-08-07"
  }

  sku {
    # Plain "Standard" isn't offered for gpt-5-nano in westeurope — Azure
    # only offers Global*/DataZone* SKUs for this model. DataZoneStandard
    # (not GlobalStandard) keeps inference traffic within the EU data zone,
    # preserving the EU-residency requirement (deployment-questionnaire.md §2)
    # that a region-pinned "Standard" deployment would have satisfied.
    name     = "DataZoneStandard"
    capacity = var.ai_foundry_capacity
  }
}

# --- Azure Functions (Flex Consumption) ---
resource "azurerm_service_plan" "functions" {
  name                = "${local.name_prefix}plan${local.name_suffix}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = var.functions_hosting_plan

  tags = local.common_tags
}

resource "azurerm_function_app_flex_consumption" "functions" {
  name                = local.functions_app_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  service_plan_id     = azurerm_service_plan.functions.id

  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${azurerm_storage_account.app_storage.primary_blob_endpoint}${azurerm_storage_container.function_deployments.name}"
  storage_authentication_type = "SystemAssignedIdentity"

  runtime_name    = "python"
  runtime_version = var.functions_python_version

  instance_memory_in_mb  = 2048
  maximum_instance_count = 100

  https_only                    = true
  virtual_network_subnet_id     = azurerm_subnet.functions.id
  public_network_access_enabled = true # ingress stays public HTTPS (FR-014 documented exception); egress to backends is forced through the VNet below

  identity {
    type = "SystemAssigned"
  }

  site_config {
    minimum_tls_version                    = var.minimum_tls_version
    vnet_route_all_enabled                 = true
    application_insights_connection_string = azurerm_application_insights.appinsights.connection_string
  }

  app_settings = {
    COSMOS_ENDPOINT              = azurerm_cosmosdb_account.cosmos.endpoint
    COSMOS_DATABASE              = azurerm_cosmosdb_sql_database.db.name
    COSMOS_CONTAINER             = azurerm_cosmosdb_sql_container.stories.name
    STORY_DRAFTS_CONTAINER       = azurerm_cosmosdb_sql_container.story_drafts.name
    STORIES_CONTAINER            = azurerm_cosmosdb_sql_container.stories.name
    STORAGE_ACCOUNT_URL          = azurerm_storage_account.app_storage.primary_blob_endpoint
    STORAGE_CONTAINER            = azurerm_storage_container.assets.name
    AZURE_OPENAI_ENDPOINT        = azurerm_cognitive_account.openai.endpoint
    AZURE_OPENAI_DEPLOYMENT_NAME = azurerm_cognitive_deployment.model.name
    # 004-story-creation's llm_service.py reads AZURE_AI_FOUNDRY_ENDPOINT
    # (research.md §1's azure-ai-inference client), not the AZURE_OPENAI_*
    # names above — same cognitive account, the name this feature's code
    # actually looks up.
    AZURE_AI_FOUNDRY_ENDPOINT        = azurerm_cognitive_account.openai.endpoint
    AZURE_AI_FOUNDRY_DEPLOYMENT_NAME = azurerm_cognitive_deployment.model.name
    LLM_INPUT_TOKEN_PRICE_USD        = var.llm_input_token_price_usd
    LLM_OUTPUT_TOKEN_PRICE_USD       = var.llm_output_token_price_usd
    AZURE_TENANT_ID                  = var.azure_tenant_id
    AZURE_APP_ID                     = var.azure_app_id != "" ? var.azure_app_id : var.azure_client_id
    SEED_ADMIN_EMAIL                 = var.seed_admin_email
    FRONTEND_URL                     = "https://${azurerm_static_web_app.web.default_host_name}/"
    PYTHON_ENABLE_WORKER_EXTENSIONS  = "true"
  }

  tags = local.common_tags

  lifecycle {
    ignore_changes = [
      # backend-deploy.yml's "Sync AzureWebJobsStorage key" step deliberately
      # sets a real storage account key out-of-band on every backend deploy —
      # Flex Consumption's Managed-Identity deployment path
      # (storage_authentication_type above) doesn't reliably load functions
      # without it (see that workflow step's comment). Without this,
      # `terraform apply` reverts the key to null on every unrelated infra
      # change and silently breaks the deployed app until the next backend
      # deploy re-syncs it.
      storage_access_key,
      # Auto-added by Azure when Application Insights is linked; not
      # Terraform-managed, and Azure just re-adds it after every apply.
      tags["hidden-link: /app-insights-resource-id"],
    ]
  }
}

# Flex Consumption pulls its own deployment package from function_deployments
# via the Function App's system-assigned identity (storage_authentication_type
# above) — a control-plane requirement distinct from the data-plane role
# assignments in identity.tf (US4/T033), which is why it's granted here
# alongside the Function App rather than there.
resource "azurerm_role_assignment" "functions_deployment_storage" {
  scope                = azurerm_storage_account.app_storage.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
}

# --- Azure Static Web App (frontend hosting) ---
# Deliberately NOT wired to the GitHub repo via repository_url/repository_token:
# github-actions-contract.md's frontend-deploy.yml deploys using this
# resource's own deployment token (output as static_web_app deployment token)
# via azure/static-web-apps-deploy@v1, rather than Azure's native GitHub
# Actions auto-integration — avoids storing a GitHub PAT in Terraform state.
resource "azurerm_static_web_app" "web" {
  name                = local.static_web_app_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  sku_tier            = "Standard"
  sku_size            = "Standard"

  tags = local.common_tags
}

# Links the Function App as this Static Web App's backend so Azure's managed
# reverse proxy routes relative /api/* calls (authService.js, accountService.js)
# through to it same-origin. Without this link, the SWA has no route for /api/*
# and returns its own 404 rather than reaching the Function App — found live
# during 003-account-provisioning-done's quickstart validation (issue #32); neither
# a linked backend nor Function App CORS had ever been provisioned.
resource "azurerm_static_web_app_function_app_registration" "web_backend" {
  static_web_app_id = azurerm_static_web_app.web.id
  function_app_id   = azurerm_function_app_flex_consumption.functions.id
}
