variable "project" { default = "bi-platform" }
variable "environment" { default = "prod" }
variable "region" { default = "us-east-1" }
variable "vpc_cidr" { default = "10.0.0.0/16" }
variable "az_count" { default = 3 }
variable "eks_version" { default = "1.30" }
variable "node_instance_types" { default = ["t3.large"] }
variable "node_min" { default = 2 }
variable "node_max" { default = 10 }
variable "db_instance_class" { default = "db.r6g.large" }
variable "domain" { default = "bi.example.com" }
variable "tags" {
  default = { Project = "bi-platform", ManagedBy = "terraform" }
}
