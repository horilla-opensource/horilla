variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "Availability zone for the database"
  type        = string
  default     = "us-east-1a"
}

variable "container_power" {
  description = "The power specification for the container service (nano, micro, small, medium, large, xlarge)"
  type        = string
  default     = "nano"
}

variable "container_scale" {
  description = "The scale specification for the container service (1-20)"
  type        = number
  default     = 1
}

variable "container_image" {
  description = "Container image URL (e.g., from ECR or Docker Hub)"
  type        = string
  # Example: "your-account.dkr.ecr.us-east-1.amazonaws.com/horilla:latest"
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "horilla"
  sensitive   = true
}

variable "db_password" {
  description = "Master password for the database"
  type        = string
  sensitive   = true
}

variable "db_bundle_id" {
  description = "Database bundle ID (micro_1_0, small_1_0, medium_1_0, large_1_0, xlarge_1_0)"
  type        = string
  default     = "micro_1_0"
}

variable "django_secret_key" {
  description = "Django SECRET_KEY for production"
  type        = string
  sensitive   = true
}

variable "allowed_hosts" {
  description = "Comma-separated list of allowed hosts for Django"
  type        = string
  default     = "hr.sahdiagnostics.com"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "hr.sahdiagnostics.com"
}

