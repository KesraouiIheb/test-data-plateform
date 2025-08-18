output "instance_connection_name" {
  description = "Connection name in the format <project>:<region>:<instance>"
  value       = module.postgis.instance_connection_name
}

output "service_account_email" {
  description = "GCP service account used by GKE for database access"
  value       = module.postgis.service_account_email
}
