# Azure stack: VNet + AKS + PostgreSQL Flexible + Redis Cache + Blob + Key Vault.
terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 3.100" }
  }
  # backend "azurerm" {}  # set via -backend-config (resource_group/storage/container)
}

provider "azurerm" { features {} }

variable "project" { default = "biplatform" }
variable "environment" { default = "prod" }
variable "location" { default = "eastus" }
variable "domain" { default = "bi.example.com" }

locals { name = "${var.project}${var.environment}" }

resource "azurerm_resource_group" "rg" {
  name     = "${local.name}-rg"
  location = var.location
}

resource "azurerm_virtual_network" "vnet" {
  name                = "${local.name}-vnet"
  address_space       = ["10.1.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "aks" {
  name                 = "aks"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.1.0.0/20"]
}

resource "azurerm_subnet" "data" {
  name                 = "data"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.1.16.0/20"]
  delegation {
    name = "postgres"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${local.name}-aks"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = local.name
  default_node_pool {
    name           = "system"
    node_count     = 2
    vm_size        = "Standard_D4s_v5"
    vnet_subnet_id = azurerm_subnet.aks.id
    auto_scaling_enabled = true
    min_count      = 2
    max_count      = 10
  }
  identity { type = "SystemAssigned" }
  network_profile {
    network_plugin = "azure"
    service_cidr   = "10.2.0.0/16"
    dns_service_ip = "10.2.0.10"
  }
  oms_agent { log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id }
}

resource "azurerm_postgresql_flexible_server" "db" {
  name                   = "${local.name}-pg"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "16"
  delegated_subnet_id    = azurerm_subnet.data.id
  private_dns_zone_id    = azurerm_private_dns_zone.pg.id
  sku_name               = "GP_Standard_D4s_v3"
  storage_mb             = 131072
  backup_retention_days  = 7
  geo_redundant_backup_enabled = true
  administrator_login    = "biadmin"
  # administrator_password -> Key Vault secret (see keyvault below).
}

resource "azurerm_private_dns_zone" "pg" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_redis_cache" "cache" {
  name                = "${local.name}-redis"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  capacity            = 1
  family              = "P"
  sku_name            = "Premium"
  enable_non_ssl_port = false
  redis_configuration { maxmemory_policy = "volatile-lru" }
}

resource "azurerm_storage_account" "assets" {
  name                     = "${lower(local.name)}assets"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  blob_properties { versioning_enabled = true }
}

resource "azurerm_key_vault" "kv" {
  name                = "${local.name}-kv"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
  purge_protection_enabled = true
}

data "azurerm_client_config" "current" {}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "${local.name}-logs"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  retention_in_days   = 90
}

output "cluster_name" { value = azurerm_kubernetes_cluster.aks.name }
output "db_fqdn" { value = azurerm_postgresql_flexible_server.db.fqdn }
output "redis_host" { value = azurerm_redis_cache.cache.hostname }
output "keyvault_uri" { value = azurerm_key_vault.kv.vault_uri }
