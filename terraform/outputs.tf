output "static_ip_address" {
  description = "Static IP address to assign to your domain"
  value       = aws_lightsail_static_ip.horilla_prod_ip.ip_address
}

output "container_service_url" {
  description = "URL of the container service"
  value       = aws_lightsail_container_service.horilla_prod.url
}

output "database_endpoint" {
  description = "Database endpoint address"
  value       = aws_lightsail_database.horilla_prod_db.master_endpoint_address
  sensitive   = true
}

output "database_port" {
  description = "Database port"
  value       = aws_lightsail_database.horilla_prod_db.master_endpoint_port
}

output "container_service_name" {
  description = "Name of the container service"
  value       = aws_lightsail_container_service.horilla_prod.name
}

