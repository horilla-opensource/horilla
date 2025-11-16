terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# LightSail Container Service for Production
resource "aws_lightsail_container_service" "horilla_prod" {
  name        = "horilla-prod"
  power       = var.container_power
  scale       = var.container_scale
  is_disabled = false

  tags = {
    Environment = "production"
    Application = "horilla"
  }
}

# Static IP for Production
resource "aws_lightsail_static_ip" "horilla_prod_ip" {
  name = "horilla-prod-static-ip"
}

# Attach Static IP to Container Service
resource "aws_lightsail_static_ip_attachment" "horilla_prod_ip_attachment" {
  static_ip_name = aws_lightsail_static_ip.horilla_prod_ip.id
  instance_name  = aws_lightsail_container_service.horilla_prod.id
}

# LightSail Database for Production (PostgreSQL)
resource "aws_lightsail_database" "horilla_prod_db" {
  relational_database_name = "horilla-prod-db"
  availability_zone        = var.availability_zone
  master_database_name     = "horilla"
  master_username          = var.db_username
  master_password          = var.db_password
  blueprint_id             = "postgres_16"
  bundle_id                = var.db_bundle_id

  publicly_accessible = false

  tags = {
    Environment = "production"
    Application = "horilla"
  }
}

# Container Service Deployment
resource "aws_lightsail_container_service_deployment_version" "horilla_prod_deployment" {
  container {
    container_name = "horilla-app"
    image          = var.container_image
    command        = ["sh", "./entrypoint.sh"]

    environment = {
      DATABASE_URL         = "postgres://${var.db_username}:${var.db_password}@${aws_lightsail_database.horilla_prod_db.master_endpoint_address}:${aws_lightsail_database.horilla_prod_db.master_endpoint_port}/${aws_lightsail_database.horilla_prod_db.master_database_name}"
      DEBUG                = "False"
      SECRET_KEY           = var.django_secret_key
      ALLOWED_HOSTS        = var.allowed_hosts
      CSRF_TRUSTED_ORIGINS = "https://${var.domain_name}"
    }

    ports = {
      "8000" = "HTTP"
    }
  }

  public_endpoint {
    container_name = "horilla-app"
    container_port = 8000
    health_check {
      healthy_threshold   = 2
      unhealthy_threshold = 2
      timeout_seconds     = 5
      interval_seconds    = 30
      path                = "/"
      success_codes       = "200-499"
    }
  }

  service_name = aws_lightsail_container_service.horilla_prod.name
}

