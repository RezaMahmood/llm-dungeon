# Role assignments for the Functions app's system-assigned Managed Identity
# (data-model.md's "Managed Identity (Function App)" entity) — Functions'
# data-plane access to Storage, Cosmos DB, and AI Foundry. Distinct from the
# functions_deployment_storage role assignment in main.tf, which grants the
# same identity control-plane access to pull its own deployment package.
#
# The GitHub OIDC Managed Identity's role assignment (Contributor, scoped to
# the Resource Group) is granted by infrastructure/scripts/bootstrap.sh via `az role
# assignment create`, not here — that identity is created outside Terraform
# (research.md §7) since Terraform itself authenticates as it.

resource "azurerm_role_assignment" "functions_storage_blob_contributor" {
  scope                = azurerm_storage_account.app_storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
}

# Cosmos DB SQL API data-plane access (actual document read/write) is
# governed by Cosmos's own RBAC system, not standard Azure RBAC — a plain
# azurerm_role_assignment against the account only grants control-plane
# permissions (e.g. listing keys), not data access. The built-in "Cosmos DB
# Built-in Data Contributor" role definition GUID below is fixed by Azure.
resource "azurerm_cosmosdb_sql_role_assignment" "functions_cosmos_data_contributor" {
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  role_definition_id  = "${azurerm_cosmosdb_account.cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
  scope               = azurerm_cosmosdb_account.cosmos.id
}

resource "azurerm_role_assignment" "functions_cognitive_services_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
}

resource "azurerm_role_assignment" "functions_monitoring_metrics_publisher" {
  scope                = azurerm_application_insights.appinsights.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
}
