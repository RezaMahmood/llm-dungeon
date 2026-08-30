terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.80.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = ">= 2.47.0"
    }
  }
}

provider "azurerm" {
  features {}

  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

# Grants the Microsoft Graph application-permission role assignments in
# identity.tf (EntraDirectoryService, T057/T058) — a separate provider block
# because Graph app-role assignment is a Microsoft Entra ID (Azure AD)
# operation, not an Azure Resource Manager one, and the azuread provider
# authenticates against Entra ID's own Graph API rather than ARM.
provider "azuread" {
  tenant_id = var.azure_tenant_id
}
