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
  description = "Embedding deployment capacity, in thousands of tokens per minute, for the GlobalStandard SKU. Keep this small on the public demo."
}

variable "acr_name" {
  type        = string
  description = "Globally unique Container Registry name. Alphanumeric only, 5 to 50 characters."
}

variable "log_analytics_workspace_name" {
  type        = string
  description = "Log Analytics workspace for the Container Apps environment."
}

variable "log_analytics_daily_quota_gb" {
  type        = number
  description = "Daily ingestion cap for the workspace, in GB. This stops log volume from becoming its own bill."
  default     = 1
}

variable "container_app_environment_name" {
  type        = string
  description = "Name of the single Container Apps environment."
}

variable "container_app_name" {
  type        = string
  description = "Name of the Container App. The public host is this name plus the environment domain."
}

variable "image_tag" {
  type        = string
  description = "Tag pushed to the registry for both the API image and the web image. A push to main applies the commit SHA. The value in terraform.tfvars is the bootstrap tag."
  default     = "1"
}

variable "github_repository" {
  type        = string
  description = "GitHub repository that may deploy main, as owner/name. This is the federated credential subject."

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must be owner/name."
  }
}

variable "deploy_container_app" {
  type        = bool
  description = "Create the Container App. Leave false until both images exist in the registry."
  default     = false
}

variable "monthly_budget_usd" {
  type        = number
  description = "Resource-group budget in USD. The alert emails at 80 and 100 percent. It does not stop spend."
  default     = 50
}

variable "budget_start_date" {
  type        = string
  description = "Budget start, first instant of a month, for example 2026-11-01T00:00:00Z. Use the first day of the current month."
}

variable "budget_alert_email" {
  type        = string
  description = "Mailbox for the budget alert. Set it only in terraform.tfvars. Do not commit that file."
  sensitive   = true
}
