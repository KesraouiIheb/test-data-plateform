variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "instance_name" {
  description = "Name of the Cloud SQL instance"
  type        = string
  default     = "metaflow-postgres"
}

variable "database_name" {
  description = "Name of the default database"
  type        = string
  default     = "pgstac"
}

variable "db_user" {
  description = "Database user for Metaflow"
  type        = string
  default     = "metaflow"
}

variable "db_password" {
  description = "Password for the database user"
  type        = string
}

variable "private_network" {
  description = "VPC network self link used for private IP"
  type        = string
}

variable "gke_namespace" {
  description = "Kubernetes namespace where Metaflow runs"
  type        = string
  default     = "default"
}

variable "k8s_service_account" {
  description = "Kubernetes service account name used by Metaflow pods"
  type        = string
  default     = "metaflow-postgres"
}
