# Outputs exported for GitHub Actions workflows and downstream consumption
# (contracts/terraform-contract.md).

output "resource_group_name" {
  value       = data.azurerm_resource_group.rg.name
  description = "Azure Resource Group name (pre-existing 'llm-dungeon' group; all project resources are provisioned into it)"
}

output "resource_group_id" {
  value       = data.azurerm_resource_group.rg.id
  description = "Azure Resource Group ID"
}

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

output "functions_app_name" {
  value       = azurerm_function_app_flex_consumption.functions.name
  description = "Azure Functions app name"
}

output "functions_app_id" {
  value       = azurerm_function_app_flex_consumption.functions.id
  description = "Azure Functions app resource ID"
}

output "functions_managed_identity_principal_id" {
  value       = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
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

output "static_web_app_deployment_token" {
  value       = azurerm_static_web_app.web.api_key
  description = "Deployment token used by frontend-deploy.yml (azure/static-web-apps-deploy@v1) — store as a repository secret, not a variable"
  sensitive   = true
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
  description = "Model deployment name (e.g., 'gpt-5-nano')"
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

output "budget_name" {
  value       = azurerm_consumption_budget_resource_group.budget.name
  description = "Name of the Resource Group budget/cost alert"
}

output "github_environment_variables" {
  value = {
    RESOURCE_GROUP_NAME          = data.azurerm_resource_group.rg.name
    FUNCTIONS_APP_NAME           = azurerm_function_app_flex_consumption.functions.name
    STORAGE_ACCOUNT_NAME         = azurerm_storage_account.app_storage.name
    COSMOS_ACCOUNT_NAME          = azurerm_cosmosdb_account.cosmos.name
    STATIC_WEB_APP_NAME          = azurerm_static_web_app.web.name
    AZURE_OPENAI_ACCOUNT_NAME    = azurerm_cognitive_account.openai.name
    AZURE_OPENAI_ENDPOINT        = azurerm_cognitive_account.openai.endpoint
    AZURE_OPENAI_DEPLOYMENT_NAME = azurerm_cognitive_deployment.model.name
  }
  description = "Environment variables for GitHub Actions (public, not secrets)"
}
