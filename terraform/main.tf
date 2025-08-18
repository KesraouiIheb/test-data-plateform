terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.22"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "postgis" {
  source              = "./postgis"
  project_id          = var.project_id
  region              = var.region
  instance_name       = var.instance_name
  database_name       = var.database_name
  db_user             = var.db_user
  db_password         = var.db_password
  private_network     = var.private_network
  gke_namespace       = var.gke_namespace
  k8s_service_account = var.k8s_service_account
}
