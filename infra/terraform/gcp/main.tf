# GCP stack: VPC + GKE + Cloud SQL Postgres + Memorystore + GCS + Secret Manager.
terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.20" }
  }
  # backend "gcs" {}  # set via -backend-config (bucket/prefix)
}

variable "project_id" {}
variable "region" { default = "us-central1" }
variable "environment" { default = "prod" }
variable "domain" { default = "bi.example.com" }

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_compute_network" "vpc" {
  name                    = "bi-${var.environment}"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "bi-${var.environment}"
  ip_cidr_range = "10.3.0.0/20"
  region        = var.region
  network       = google_compute_network.vpc.id
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.4.0.0/16"
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.5.0.0/20"
  }
}

resource "google_container_cluster" "gke" {
  name     = "bi-${var.environment}"
  location = var.region
  network  = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  node_pool {
    name               = "default"
    initial_node_count = 2
    autoscaling { min_node_count = 2, max_node_count = 10 }
    node_config {
      machine_type = "e2-standard-4"
      oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    }
    management { auto_upgrade = true, auto_repair = true }
  }
  workload_identity_config { workload_pool = "${var.project_id}.svc.id.goog" }
}

resource "google_sql_database_instance" "postgres" {
  name             = "bi-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region
  settings {
    tier              = "db-custom-4-16384"
    availability_type = "REGIONAL"
    disk_autoresize   = true
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      backup_retention_settings { retained_backups = 7 }
    }
    ip_configuration { private_network = google_compute_network.vpc.id }
  }
  deletion_protection = true
}

resource "google_redis_instance" "cache" {
  name           = "bi-${var.environment}"
  tier           = "STANDARD_HA"
  memory_size_gb = 5
  region         = var.region
  authorized_network = google_compute_network.vpc.id
  redis_version  = "REDIS_7_0"
  auth_enabled   = true
}

resource "google_storage_bucket" "assets" {
  name          = "${var.project_id}-bi-assets"
  location      = var.region
  force_destroy = false
  versioning { enabled = true }
  encryption { default_kms_key_name = google_kms_crypto_key.assets.id }
}

resource "google_kms_key_ring" "ring" {
  name     = "bi-${var.environment}"
  location = var.region
}

resource "google_kms_crypto_key" "assets" {
  name     = "assets"
  key_ring = google_kms_key_ring.ring.id
  rotation_period = "7776000s"  # 90d rotation
}

resource "google_secret_manager_secret" "app" {
  secret_id = "bi-${var.environment}-app"
  replication { auto {} }
}

output "cluster_name" { value = google_container_cluster.gke.name }
output "db_connection" { value = google_sql_database_instance.postgres.connection_name }
output "redis_host" { value = google_redis_instance.cache.host }
output "assets_bucket" { value = google_storage_bucket.assets.name }
