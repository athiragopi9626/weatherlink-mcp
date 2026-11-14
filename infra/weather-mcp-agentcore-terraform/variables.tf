variable "aws_region" {
  description = "AWS Region where AgentCore Runtime is available."
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Short lowercase prefix for AWS resources."
  type        = string
  default     = "weather-mcp"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "cognito_domain_prefix" {
  description = "Globally unique Cognito hosted domain prefix in this Region."
  type        = string
}

variable "image_tag" {
  description = "Immutable container image tag already pushed to ECR."
  type        = string
  default     = "v1"
}

variable "deploy_runtime" {
  description = "Set true after pushing ARM64 image to ECR."
  type        = bool
  default     = false
}

variable "metoffice_secret_arn" {
  description = "Optional existing Secrets Manager secret ARN holding Met Office API key; app must read it at runtime."
  type        = string
  default     = ""
}

variable "tags" {
  type = map(string)
  default = {
    ManagedBy = "Terraform"
    Project   = "weather-mcp"
  }
}
