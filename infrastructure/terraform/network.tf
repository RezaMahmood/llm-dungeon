# Virtual Network, subnets, and (added in Phase 6 / User Story 4) private
# endpoints and Private DNS Zones. data-model.md's Virtual Network,
# Private Endpoints, and Private DNS Zones entities.
#
# Unlike the pre-existing Resource Group, this VNet IS Terraform-managed
# (research.md §6, §8).

resource "azurerm_virtual_network" "vnet" {
  name                = local.vnet_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  address_space       = var.vnet_address_space
  tags                = local.common_tags
}

# Functions VNet-integration subnet — delegated to Microsoft.App/environments
# so a Flex Consumption Function App can integrate natively (research.md §3).
resource "azurerm_subnet" "functions" {
  name                 = local.functions_subnet_name
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.functions_subnet_prefix]

  delegation {
    name = "functions-delegation"

    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Private endpoints subnet — hosts the private endpoints for Storage, Cosmos
# DB, and AI Foundry (added in identity/network resources below).
resource "azurerm_subnet" "private_endpoints" {
  name                 = local.private_endpoints_subnet_name
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.private_endpoints_subnet_prefix]

  private_endpoint_network_policies = "Disabled"
}

# --- Private DNS Zones (data-model.md's Private DNS Zones entity) ---

resource "azurerm_private_dns_zone" "blob" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = data.azurerm_resource_group.rg.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone" "cosmos" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = data.azurerm_resource_group.rg.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone" "openai" {
  name                = "privatelink.openai.azure.com"
  resource_group_name = data.azurerm_resource_group.rg.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "blob" {
  name                = "${local.vnet_name}-blob-link"
  private_dns_zone_id = azurerm_private_dns_zone.blob.id
  virtual_network_id  = azurerm_virtual_network.vnet.id
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "cosmos" {
  name                = "${local.vnet_name}-cosmos-link"
  private_dns_zone_id = azurerm_private_dns_zone.cosmos.id
  virtual_network_id  = azurerm_virtual_network.vnet.id
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "openai" {
  name                = "${local.vnet_name}-openai-link"
  private_dns_zone_id = azurerm_private_dns_zone.openai.id
  virtual_network_id  = azurerm_virtual_network.vnet.id
  tags                = local.common_tags
}

# --- Private Endpoints (data-model.md's Private Endpoints entity) ---

resource "azurerm_private_endpoint" "storage" {
  name                = "${local.name_prefix}pe-storage${local.name_suffix}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.common_tags

  private_service_connection {
    name                           = "storage-privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.app_storage.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "storage-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }
}

resource "azurerm_private_endpoint" "cosmos" {
  name                = "${local.name_prefix}pe-cosmos${local.name_suffix}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.common_tags

  private_service_connection {
    name                           = "cosmos-privateserviceconnection"
    private_connection_resource_id = azurerm_cosmosdb_account.cosmos.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "cosmos-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos.id]
  }
}

resource "azurerm_private_endpoint" "openai" {
  name                = "${local.name_prefix}pe-openai${local.name_suffix}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.common_tags

  private_service_connection {
    name                           = "openai-privateserviceconnection"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "openai-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.openai.id]
  }
}
