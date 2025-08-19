variable "project_id" {
  description = "GCP project id"
}

variable "region" {
  description = "GCP region"
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone"
  default     = "us-central1-a"
}

variable "network" {
  description = "VPC network self link"
  default     = "default"
}

variable "machine_type" {
  description = "Machine type for the VMs"
  default     = "e2-medium"
}

variable "image" {
  description = "Image for boot disk"
  default     = "debian-cloud/debian-12"
}

variable "disk_size" {
  description = "Boot disk size in GB"
  default     = 50
}
