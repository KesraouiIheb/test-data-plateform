variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
}

variable "instance_name" {
  type        = string
  description = "Cloud SQL instance name"
}

variable "database_name" {
  type        = string
  description = "Database to create"
}

variable "db_user" {
  type        = string
  description = "Database user"
}

variable "db_password" {
  type        = string
  description = "Password for the database user"
}

variable "private_network" {
  type        = string
  description = "VPC network self link for private IP"
}

variable "gke_namespace" {
  type        = string
  description = "Namespace where Metaflow pods run"
}

variable "k8s_service_account" {
  type        = string
  description = "Kubernetes service account name"
}
