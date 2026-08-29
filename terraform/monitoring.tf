# Log Analytics Workspace, workspace-based Application Insights, and the
# Resource Group budget/cost alert (data-model.md's Log Analytics Workspace,
# Application Insights, and Budget & Cost Alert entities).

resource "azurerm_log_analytics_workspace" "logs" {
  name                = local.log_analytics_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = var.log_analytics_retention_days
  tags                = local.common_tags
}

resource "azurerm_application_insights" "appinsights" {
  name                 = local.app_insights_name
  resource_group_name  = data.azurerm_resource_group.rg.name
  location             = data.azurerm_resource_group.rg.location
  application_type     = "web"
  workspace_id         = azurerm_log_analytics_workspace.logs.id
  retention_in_days    = var.log_analytics_retention_days
  daily_data_cap_in_gb = 5
  tags                 = local.common_tags
}

resource "azurerm_consumption_budget_resource_group" "budget" {
  name              = "${local.name_prefix}budget${local.name_suffix}"
  resource_group_id = data.azurerm_resource_group.rg.id

  amount     = var.budget_amount_usd
  time_grain = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", timestamp())
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = [var.budget_alert_email]
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = [var.budget_alert_email]
  }

  lifecycle {
    ignore_changes = [time_period[0].start_date]
  }
}
