locals {
  # Naming convention (data-model.md "Terraform Configuration" entity):
  #   {prefix}-{resource-type}-{environment}          e.g. llmdungeon-func-prod
  # Storage Accounts are the documented exception (Azure disallows hyphens in
  # storage account names):
  #   {prefix}{resource-type}{environment}             e.g. llmdungeonassetsprod
  name_prefix        = "${var.resource_prefix}-"
  name_suffix        = "-${var.environment == "production" ? "prod" : var.environment}"
  storage_name_infix = var.environment == "production" ? "prod" : var.environment

  vnet_name                     = "${local.name_prefix}vnet${local.name_suffix}"
  functions_subnet_name         = "${local.name_prefix}snet-func${local.name_suffix}"
  private_endpoints_subnet_name = "${local.name_prefix}snet-pe${local.name_suffix}"

  functions_app_name   = "${local.name_prefix}func${local.name_suffix}"
  static_web_app_name  = "${local.name_prefix}web${local.name_suffix}"
  cosmos_account_name  = "${local.name_prefix}cosmos${local.name_suffix}"
  cosmos_database_name = "${local.name_prefix}db${local.name_suffix}"
  openai_account_name  = "${local.name_prefix}openai${local.name_suffix}"
  log_analytics_name   = "${local.name_prefix}logs${local.name_suffix}"
  app_insights_name    = "${local.name_prefix}appinsights${local.name_suffix}"
  dashboard_name       = "${local.name_prefix}dash${local.name_suffix}"

  # Storage account names: hyphen-free per data-model.md
  storage_assets_name = "${var.resource_prefix}assets${local.storage_name_infix}"

  # Common tags applied to every resource (data-model.md, terraform-contract.md)
  common_tags = merge(var.tags, {
    environment = var.environment
  })
}
