variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "image_tag" {
  description = "Docker image tag to deploy (git commit SHA)"
  type        = string
  default     = "latest"
}

# Sensitive — set in terraform.tfvars (never committed to git)
variable "tavily_api_key" {
  description = "Tavily API key — stored in Key Vault"
  type        = string
  sensitive   = true
}

variable "postgres_admin_password" {
  description = "PostgreSQL admin password — stored in Key Vault"
  type        = string
  sensitive   = true
}
