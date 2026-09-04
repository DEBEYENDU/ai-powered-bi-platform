output "cluster_name" { value = module.eks.cluster_name }
output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "db_endpoint" { value = aws_db_instance.postgres.endpoint }
output "redis_endpoint" { value = aws_elasticache_replication_group.redis.primary_endpoint_address }
output "assets_bucket" { value = aws_s3_bucket.assets.bucket }
output "tls_cert_arn" { value = aws_acm_certificate.tls.arn }
output "app_secret_arn" { value = aws_secretsmanager_secret.app.arn }
