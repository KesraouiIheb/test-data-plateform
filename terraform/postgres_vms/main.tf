terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_compute_instance" "ingest" {
  name         = "ingest-postgres"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = var.image
      size  = var.disk_size
    }
  }

  network_interface {
    network = var.network
    access_config {}
  }

  metadata_startup_script = file("${path.module}/install_postgres.sh")
}

resource "google_compute_instance" "pgstac" {
  name         = "pgstac-postgres"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = var.image
      size  = var.disk_size
    }
  }

  network_interface {
    network = var.network
    access_config {}
  }

  metadata_startup_script = file("${path.module}/install_pgstac.sh")
}
