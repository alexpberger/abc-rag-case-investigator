output "openai_endpoint" {
  description = "Value for AZURE_OPENAI_ENDPOINT. Copy it into .env. Do not commit Terraform state; state can contain secrets even though this output does not."
  value       = azurerm_cognitive_account.openai.endpoint
}

output "chat_deployment_name" {
  description = "Value for AZURE_OPENAI_CHAT_DEPLOYMENT."
  value       = azurerm_cognitive_deployment.chat.name
}

output "embedding_deployment_name" {
  description = "Value for AZURE_OPENAI_EMBEDDING_DEPLOYMENT."
  value       = azurerm_cognitive_deployment.embedding.name
}

output "acr_name" {
  description = "Registry name for az acr build."
  value       = azurerm_container_registry.main.name
}

output "acr_login_server" {
  description = "Registry host used in the Container App image names."
  value       = azurerm_container_registry.main.login_server
}

output "container_app_url" {
  description = "Public HTTPS origin. Empty until deploy_container_app is true."
  value       = var.deploy_container_app ? "https://${azurerm_container_app.web[0].ingress[0].fqdn}" : ""
}

output "github_actions_client_id" {
  description = "Value for the AZURE_CLIENT_ID GitHub secret. This is the deploy identity, not an application password."
  value       = azurerm_user_assigned_identity.github.client_id
}

output "tenant_id" {
  description = "Value for the AZURE_TENANT_ID GitHub secret."
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Value for the AZURE_SUBSCRIPTION_ID GitHub secret."
  value       = data.azurerm_client_config.current.subscription_id
}
