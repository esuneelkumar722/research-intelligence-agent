# Uncomment and configure to store Terraform state in Azure Blob Storage.
# Create the storage account once manually (bootstrap), then uncomment.
#
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "rg-tfstate"
#     storage_account_name = "<your_storage_account>"
#     container_name       = "tfstate"
#     key                  = "research-agent.terraform.tfstate"
#   }
# }
