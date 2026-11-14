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
