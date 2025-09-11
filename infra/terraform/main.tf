terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.111.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = ">= 1.13.0"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "location" { type = string }
variable "env" { type = string }
variable "base_name" { type = string }

locals {
  rg_name      = "${var.base_name}-${var.env}-rg"
  storage_name = lower(replace("${var.base_name}stor", "-", ""))
  func_name    = lower("${var.base_name}-${var.env}-func")
  cosmos_name  = lower(replace("${var.base_name}-cosmos", "_", ""))
  search_name  = lower(replace("${var.base_name}-search", "_", ""))
  comm_name    = lower(replace("${var.base_name}-comm", "_", ""))
  cog_name     = lower(replace("${var.base_name}-cog", "_", ""))
}

resource "azurerm_resource_group" "rg" {
  name     = local.rg_name
  location = var.location
}

resource "azurerm_storage_account" "sa" {
  name                     = local.storage_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  allow_nested_items_to_be_public = false
}

resource "azurerm_cosmosdb_account" "cosmos" {
  name                = local.cosmos_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Eventual"
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
  }

  capability { name = "EnableServerless" }
}

resource "azurerm_cosmosdb_sql_database" "db" {
  name                = "validation-tracking"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
}

resource "azurerm_cosmosdb_sql_container" "metadata" {
  name                  = "file-metadata"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_path    = "/file_id"
}

resource "azurerm_cosmosdb_sql_container" "validations" {
  name                  = "validation-results"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_path    = "/file_id"
}

resource "azurerm_cosmosdb_sql_container" "emails" {
  name                  = "email-notifications"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_path    = "/file_id"
}

resource "azurerm_cosmosdb_sql_container" "tracking" {
  name                  = "change-tracking"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_path    = "/file_id"
}

resource "azurerm_communication_service" "comm" {
  name                = local.comm_name
  resource_group_name = azurerm_resource_group.rg.name
  data_location       = "United States"
}

resource "azurerm_cognitive_account" "docint" {
  name                = local.cog_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  kind                = "FormRecognizer"
  sku_name            = "S0"
}

resource "azurerm_search_service" "search" {
  name                = local.search_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "basic"
  partition_count     = 1
  replica_count       = 1
}

resource "azurerm_app_service_plan" "plan" {
  name                = "${var.base_name}-${var.env}-plan"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "Linux"
  reserved            = true

  sku {
    tier = "Dynamic"
    size = "Y1"
  }
}

resource "azurerm_linux_function_app" "func" {
  name                = local.func_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  service_plan_id     = azurerm_app_service_plan.plan.id
  storage_account_name       = azurerm_storage_account.sa.name
  storage_account_access_key = azurerm_storage_account.sa.primary_access_key

  site_config {
    application_stack {
      python_version = "3.10"
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME                      = "python"
    AzureWebJobsStorage                            = azurerm_storage_account.sa.primary_connection_string
    AZURE_STORAGE_CONNECTION_STRING                = azurerm_storage_account.sa.primary_connection_string
    AZURE_COSMOSDB_CONNECTION_STRING               = azurerm_cosmosdb_account.cosmos.connection_strings[0]
    AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING = azurerm_communication_service.comm.primary_connection_string
  }
}

# Optional: Microsoft Fabric workspace via AzAPI (requires RP registered)
resource "azapi_resource" "fabric_ws" {
  type      = "Microsoft.Fabric/workspaces@2023-11-01-preview"
  name      = "${var.base_name}-${var.env}-fabric"
  location  = var.location
  parent_id = azurerm_resource_group.rg.id
  body = jsonencode({ properties = { } })
  lifecycle { ignore_changes = [ body ] }
}

output function_app_name { value = azurerm_linux_function_app.func.name }
output storage_account_name { value = azurerm_storage_account.sa.name }
output cosmos_account_name { value = azurerm_cosmosdb_account.cosmos.name }
output search_service_name { value = azurerm_search_service.search.name }
output communication_service_name { value = azurerm_communication_service.comm.name }
output cognitive_services_name { value = azurerm_cognitive_account.docint.name }
