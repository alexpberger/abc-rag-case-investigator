# Public demo: one Container Apps environment, one app, three containers.
# nginx is the only container with ingress. The API and Postgres listen on localhost inside the replica.
# Postgres uses an emptyDir volume. Azure Files (SMB) does not provide the file locks Postgres needs.
# A new replica starts empty and app.serve re-embeds the Markdown files once. Unchanged files are skipped.

resource "random_password" "postgres" {
  length  = 32
  special = false
}

resource "azurerm_container_registry" "main" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = var.log_analytics_workspace_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = var.log_analytics_daily_quota_gb
}

resource "azurerm_container_app_environment" "main" {
  name                       = var.container_app_environment_name
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

resource "azurerm_user_assigned_identity" "app" {
  name                = "${var.container_app_name}-pull"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_container_app" "web" {
  count                        = var.deploy_container_app ? 1 : 0
  name                         = var.container_app_name
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  secret {
    name  = "postgres-password"
    value = random_password.postgres.result
  }

  secret {
    name  = "database-url"
    value = "postgresql://postgres:${random_password.postgres.result}@127.0.0.1:5432/cases"
  }

  secret {
    name  = "azure-openai-api-key"
    value = azurerm_cognitive_account.openai.primary_access_key
  }

  ingress {
    external_enabled = true
    target_port      = 80
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    volume {
      name         = "pgdata"
      storage_type = "EmptyDir"
    }

    container {
      name   = "web"
      image  = "${azurerm_container_registry.main.login_server}/abc-rag-web:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      liveness_probe {
        transport               = "HTTP"
        port                    = 80
        path                    = "/"
        interval_seconds        = 10
        timeout                 = 1
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 80
        path                    = "/"
        interval_seconds        = 10
        timeout                 = 1
        failure_count_threshold = 3
        success_count_threshold = 3
      }
    }

    container {
      name   = "api"
      image  = "${azurerm_container_registry.main.login_server}/abc-rag-api:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.openai.endpoint
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-10-21"
      }
      env {
        name  = "AZURE_OPENAI_CHAT_DEPLOYMENT"
        value = azurerm_cognitive_deployment.chat.name
      }
      env {
        name  = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        value = azurerm_cognitive_deployment.embedding.name
      }
      env {
        name  = "EMBEDDING_DIMENSIONS"
        value = "1536"
      }
      env {
        name  = "KNOWLEDGE_DIR"
        value = "/app/knowledge"
      }
      env {
        name  = "CORS_ORIGINS"
        value = "https://${var.container_app_name}.${azurerm_container_app_environment.main.default_domain}"
      }
      env {
        name  = "TRUST_PROXY"
        value = "true"
      }
      env {
        name  = "EXPOSE_API_DOCS"
        value = "false"
      }
      env {
        name  = "INVESTIGATE_DAILY_LIMIT"
        value = "100"
      }
      env {
        name  = "ASK_DAILY_LIMIT"
        value = "300"
      }
      env {
        name  = "INVESTIGATE_HOURLY_LIMIT"
        value = "10"
      }
      env {
        name  = "ASK_HOURLY_LIMIT"
        value = "30"
      }

      startup_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/api/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 60
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/api/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
      }
    }

    container {
      name   = "postgres"
      image  = "pgvector/pgvector:pg16"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "POSTGRES_USER"
        value = "postgres"
      }
      env {
        name        = "POSTGRES_PASSWORD"
        secret_name = "postgres-password"
      }
      env {
        name  = "POSTGRES_DB"
        value = "cases"
      }

      volume_mounts {
        name = "pgdata"
        path = "/var/lib/postgresql/data"
      }

      startup_probe {
        transport               = "TCP"
        port                    = 5432
        interval_seconds        = 5
        timeout                 = 1
        failure_count_threshold = 24
      }

      liveness_probe {
        transport               = "TCP"
        port                    = 5432
        interval_seconds        = 10
        timeout                 = 1
        failure_count_threshold = 3
      }
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}

# GitHub Actions on main signs in as this identity. No client secret.
# Contributor covers image builds and the Container App. User Access Administrator
# is required so a later apply can read the role assignments in this stack.
# The state account is the one named in backend.tf. Its id is built here instead of
# read with a data source: this identity can assign roles on that account, and it
# cannot read the account resource in the other resource group.
# The applying account must be allowed to create role assignments.

data "azurerm_client_config" "current" {}

locals {
  tfstate_storage_account_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/rg-abc-rag-tfstate/providers/Microsoft.Storage/storageAccounts/stabcragln2041"
}

resource "azurerm_user_assigned_identity" "github" {
  name                = "${var.container_app_name}-github"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_federated_identity_credential" "github_main" {
  name                      = "github-main"
  user_assigned_identity_id = azurerm_user_assigned_identity.github.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = "repo:${var.github_repository}:ref:refs/heads/main"
}

resource "azurerm_role_assignment" "github_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "github_role_admin" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "User Access Administrator"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "github_state" {
  scope                = local.tfstate_storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "github_state_role_admin" {
  scope                = local.tfstate_storage_account_id
  role_definition_name = "User Access Administrator"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "budget-${var.resource_group_name}"
  resource_group_id = azurerm_resource_group.main.id
  amount            = var.monthly_budget_usd
  time_grain        = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.budget_alert_email]
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Forecasted"
    contact_emails = [var.budget_alert_email]
  }
}
