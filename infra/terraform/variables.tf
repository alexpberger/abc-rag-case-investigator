variable "location" {
  type        = string
  description = "Azure region. Confirm model availability in this region before apply. Do not hard-code the region in main.tf."
}

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group that holds the Azure OpenAI account."
}

variable "openai_account_name" {
  type        = string
  description = "Globally unique Cognitive Services account name. Also used as the custom subdomain."
}

variable "chat_deployment_name" {
  type        = string
  description = "Deployment name the API uses as AZURE_OPENAI_CHAT_DEPLOYMENT."
}

variable "chat_model_name" {
  type        = string
  description = "Chat model name, for example gpt-4.1. Confirm the current catalog name before apply."
}

variable "chat_model_version" {
  type        = string
  description = "Chat model version string required by Azure for the chosen model."
}

variable "chat_capacity" {
  type        = number
  description = "Chat deployment capacity, in thousands of tokens per minute, for the GlobalStandard SKU."
}

variable "embedding_deployment_name" {
  type        = string
  description = "Deployment name the API uses as AZURE_OPENAI_EMBEDDING_DEPLOYMENT."
}

variable "embedding_model_name" {
  type        = string
  description = "Embedding model name. V1 expects text-embedding-3-small so the vector width stays 1536."
}

variable "embedding_model_version" {
  type        = string
  description = "Embedding model version string required by Azure."
}

variable "embedding_capacity" {
  type        = number
  description = "Embedding deployment capacity, in thousands of tokens per minute, for the GlobalStandard SKU."
}
