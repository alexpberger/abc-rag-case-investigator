# Remote state for this stack. It names the storage account and does not contain the budget mailbox or API keys.
# use_azuread_auth keeps the storage account key out of this configuration.

terraform {
  backend "azurerm" {
    resource_group_name  = "rg-abc-rag-tfstate"
    storage_account_name = "stabcragln2041"
    container_name       = "tfstate"
    key                  = "abc-rag.tfstate"
    use_azuread_auth     = true
    use_oidc             = true
  }
}
