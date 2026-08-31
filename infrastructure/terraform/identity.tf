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

resource "azurerm_role_assignment" "functions_cognitive_services_openai_user" {
  scope = azurerm_cognitive_account.openai.id
  # "Cognitive Services User" (the role this previously granted) only covers
  # read/listKeys control-plane actions — it does not include the
  # Microsoft.CognitiveServices/accounts/OpenAI/* data actions llm_service.py's
  # DefaultAzureCredential-authenticated inference calls need, which surfaced
  # as a 403 AuthorizationFailed on every Suggest call during T033 manual
  # acceptance (2026-08-31).
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
}

resource "azurerm_role_assignment" "functions_monitoring_metrics_publisher" {
  scope                = azurerm_application_insights.appinsights.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
}

# --- Microsoft Graph application permissions (EntraDirectoryService, T057/T058) ---
# Grants the Function App's system-assigned Managed Identity application-level
# (not delegated) Graph permissions to invite (FR-011) and remove (FR-013)
# Entra ID guest users, matching EntraDirectoryService's use of
# DefaultAzureCredential against https://graph.microsoft.com/.default. An
# azuread_app_role_assignment against an application permission constitutes
# admin consent — no separate consent step is required.

# Well-known application ID for the Microsoft Graph service principal —
# fixed by Microsoft in every tenant, not something Terraform creates.
data "azuread_service_principal" "msgraph" {
  client_id = "00000003-0000-0000-c000-000000000000"
}

resource "azuread_app_role_assignment" "functions_graph_user_invite_all" {
  app_role_id         = data.azuread_service_principal.msgraph.app_role_ids["User.Invite.All"]
  principal_object_id = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
  resource_object_id  = data.azuread_service_principal.msgraph.object_id
}

# Scoped delete permission for remove_guest (T057) — User.ReadWrite.All is the
# narrowest built-in Graph application role that includes deleting a guest
# user; there is no permission scoped to "delete guest users" alone.
resource "azuread_app_role_assignment" "functions_graph_user_readwrite_all" {
  app_role_id         = data.azuread_service_principal.msgraph.app_role_ids["User.ReadWrite.All"]
  principal_object_id = azurerm_function_app_flex_consumption.functions.identity[0].principal_id
  resource_object_id  = data.azuread_service_principal.msgraph.object_id
}
