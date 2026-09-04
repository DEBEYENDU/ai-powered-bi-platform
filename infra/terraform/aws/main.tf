# AWS stack: VPC + EKS + RDS Postgres + ElastiCache + S3 + ACM/DNS.
# Secrets land in AWS Secrets Manager; EKS reads them via External Secrets.
data "aws_availability_zones" "available" {}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags = { Name = "${var.project}-${var.environment}" }
}

resource "aws_subnet" "public" {
  count                   = var.az_count
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name                                        = "${var.project}-public-${count.index}"
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.project}-eks" = "shared"
  }
}

resource "aws_subnet" "private" {
  count             = var.az_count
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = {
    Name                                             = "${var.project}-private-${count.index}"
    "kubernetes.io/role/internal-elb"                = "1"
    "kubernetes.io/cluster/${var.project}-eks"      = "shared"
  }
}

resource "aws_internet_gateway" "igw" { vpc_id = aws_vpc.main.id }
resource "aws_eip" "nat" { count = var.az_count }
resource "aws_nat_gateway" "nat" {
  count         = var.az_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "~> 20.0"
  cluster_name    = "${var.project}-eks"
  cluster_version = var.eks_version
  vpc_id          = aws_vpc.main.id
  subnet_ids      = aws_subnet.private[*].id
  eks_managed_node_groups = {
    default = {
      instance_types = var.node_instance_types
      min_size       = var.node_min
      max_size       = var.node_max
    }
  }
}

resource "aws_db_subnet_group" "db" {
  name       = "${var.project}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.project}-postgres"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.db_instance_class
  allocated_storage      = 100
  storage_encrypted      = true
  db_subnet_group_name   = aws_db_subnet_group.db.name
  backup_retention_period = 7
  deletion_protection    = true
  # NOTE: enable pgvector via parameter group + CREATE EXTENSION vector.
  # username/password managed in Secrets Manager (see outputs + runbook).
  skip_final_snapshot = false
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project}-redis"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.project}-redis"
  description          = "BI platform cache"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = "cache.t3.micro"
  num_cache_clusters   = 2
  automatic_failover_enabled = true
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}

resource "aws_s3_bucket" "assets" {
  bucket = "${var.project}-${var.environment}-assets"
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}

resource "aws_acm_certificate" "tls" {
  domain_name       = var.domain
  validation_method = "DNS"
}

resource "aws_secretsmanager_secret" "app" {
  name = "${var.project}/${var.environment}/app"
}
