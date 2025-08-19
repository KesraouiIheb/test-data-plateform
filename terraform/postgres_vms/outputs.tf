output "ingest_vm_ip" {
  value = google_compute_instance.ingest.network_interface[0].access_config[0].nat_ip
}

output "pgstac_vm_ip" {
  value = google_compute_instance.pgstac.network_interface[0].access_config[0].nat_ip
}
