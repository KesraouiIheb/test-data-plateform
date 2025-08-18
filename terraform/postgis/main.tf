provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "cloudsql" {
  account_id   = "${var.instance_name}-client"
  display_name = "Cloud SQL client for Metaflow"
}

resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloudsql.email}"
}

resource "google_service_account_iam_binding" "workload_identity" {
  service_account_id = google_service_account.cloudsql.name
  role               = "roles/iam.workloadIdentityUser"
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[${var.gke_namespace}/${var.k8s_service_account}]"
  ]
}

resource "google_sql_database_instance" "postgres" {
  name             = var.instance_name
  database_version = "POSTGRES_15"
  region           = var.region
  root_password    = var.db_password

  settings {
    tier              = var.db_tier
    disk_size         = var.db_disk_size_gb
    availability_type = "REGIONAL"
    backup_configuration {
      enabled = true
    }
    ip_configuration {
      ipv4_enabled    = false
      private_network = var.private_network
      require_ssl     = true
    }
  }
}

resource "google_sql_user" "dbuser" {
  name     = var.db_user
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

resource "google_sql_database" "pgstac" {
  name     = var.database_name
  instance = google_sql_database_instance.postgres.name
}

provider "postgresql" {
  host            = google_sql_database_instance.postgres.private_ip_address
  port            = 5432
  username        = google_sql_user.dbuser.name
  password        = var.db_password
  database        = google_sql_database.pgstac.name
  sslmode         = "require"
}

resource "postgresql_extension" "postgis" {
  name = "postgis"
}

resource "postgresql_extension" "pgstac" {
  name = "pgstac"
}

output "instance_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "service_account_email" {
  value = google_service_account.cloudsql.email
}
