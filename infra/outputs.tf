output "backend_url" {
  description = "Public URL of the backend Container App"
  value       = module.container_apps.backend_url
}

output "acr_login_server" {
  description = "ACR login server for docker push"
  value       = module.container_registry.login_server
}

output "key_vault_url" {
  description = "Key Vault URI for secret references"
  value       = module.key_vault.vault_uri
}

output "app_insights_connection_string" {
  description = "App Insights connection string for APPLICATIONINSIGHTS_CONNECTION_STRING"
  value       = module.monitoring.app_insights_connection_string
  sensitive   = true
}
