# Phase 16 – DevOps, Cloud Deployment, Security Hardening & Production Readiness

## Architecture

```
Client → CDN → Load Balancer → Nginx (TLS, rate-limit, cache)
  → Frontend (SPA) ─┐
  → FastAPI Backend (gunicorn × N) → Redis → Celery workers → scheduler
  → Analytics/AI/ML engines → PostgreSQL (+pgvector) → Object storage
  → Prometheus/Grafana/Alertmanager → Backups
```

Single-node: `infra/compose/prod.yml`. HA: Kubernetes (`infra/k8s`) or Helm
(`infra/helm`) with managed DB/Redis (Terraform).

## Environments

| Env | How | Images |
|---|---|---|
| dev | `compose/dev.yml` (hot-reload, pgAdmin/MinIO profiles) | local build |
| test | `compose/test.yml` (ephemeral, runs pytest + smoke) | local build |
| staging | `compose/staging.yml` or Helm + `values-staging.yaml` | GHCR `:staging` |
| prod | `compose/prod.yml` or Helm + `values-prod.yaml` | GHCR `:vX.Y.Z` |

## Containers

- `infra/docker/backend.prod.Dockerfile` — multi-stage, non-root (10001),
  gunicorn+uvicorn, healthcheck, migrate-on-boot entrypoint.
- `infra/docker/backend.dev.Dockerfile` — reload server for dev/test.
- `infra/docker/frontend.prod.Dockerfile` — node build + nginx static (user 10002).
- Worker/scheduler reuse the backend image with Celery commands.

## Kubernetes / Helm

- `infra/k8s/base`: namespaces, config, secret placeholders, postgres/redis
  StatefulSets, api (HPA 3–20, PDB), workers (HPA + KEDA note), scheduler,
  frontend, TLS ingress, NetworkPolicies, quota/limits, migrate Job, backup CronJob.
- `infra/helm/bi-platform`: Chart + `values.yaml` + staging/prod overlays,
  Bitnami postgres/redis subcharts for dev, external DB/Redis for stage/prod.
- Replace `ghcr.io/ORG` + `TAG` at deploy time (`infra/scripts/deploy.sh`).

## CI/CD (`.github/workflows`)

- `ci.yml` — ruff, unit tests, integration tests (pgvector + redis services),
  image builds.
- `security.yml` — gitleaks, pip-audit, Trivy→SARIF (weekly schedule too).
- `cd-staging.yml` — push `:staging`, Helm deploy, rollout status, smoke test.
- `cd-prod.yml` — tag-triggered, protected environment (approvals), smoke test,
  automatic `helm rollback` on smoke failure.

## Terraform (`infra/terraform`)

- AWS: VPC + NAT, EKS, RDS Postgres 16, ElastiCache Redis HA, S3 (versioned/SSE),
  ACM cert, Secrets Manager entry.
- Azure: VNet, AKS (autoscale), Postgres Flexible (HA, PITR), Premium Redis,
  GRS storage, Key Vault, Log Analytics.
- GCP: VPC, GKE (autopilot-ready pools), Cloud SQL HA+PITR, Memorystore HA,
  GCS (KMS, 90-day rotation), Secret Manager.
- Remote state backends sketched (commented) — configure per org.

## Reverse Proxy / TLS

`infra/nginx`: `nginx.conf` (TLS 1.2+, HSTS, gzip, 100r/m API + 10r/m login
limits, static cache), `conf.d/bi.conf` (routing, CSP/frame headers, 100 MB
uploads), `frontend.conf` (SPA + immutable assets). Staging certs:
`scripts/generate-certs.sh`; prod via cert-manager (k8s) or ACM.

## Observability

- Prometheus scrape config + 9 alert rules (down, CPU/mem, latency, errors,
  queue, disk, cert expiry, stale backups).
- Grafana dashboards: platform overview, AI & reports.
- App exposes `GET /admin/metrics/prometheus`; traces at `/admin/traces`.

## Backup & DR

- `scripts/backup.sh` — pg_dump custom format, verify via `pg_restore --list`,
  14-day retention, timestamp marker for the BackupStale alert.
- `scripts/restore.sh` — typed-confirmation restore into a target DB.
- K8s CronJob runs backups nightly to a 100 Gi PVC.
- DR runbook: restore → `alembic upgrade head` → smoke test → switch traffic
  (blue-green via second Helm release or compose TAG swap).

## Secrets

See `infra/security/secrets-management.md`. TL;DR: no secrets in code/images;
vault-injected env (compose), Sealed/External Secrets (k8s); 90-day KMS
rotation; overlapping JWT rotation.

## Security Hardening

Checklist + OWASP mapping in `infra/security/`. Highlights: non-root
read-only containers, dropped caps, seccomp, default-deny network, Trivy +
pip-audit + gitleaks gates, short JWT lifetimes, audit-everything.

## Release Management

SemVer tags (`v*`) trigger prod pipeline. Staging auto-deploys from `main`.
Blue-green: deploy second Helm release, switch ingress. Canary: Helm
canary weights (ingress-nginx canary annotations) + feature flags for app-level
gating. Rollback: `helm rollback` (auto on smoke failure) or previous compose TAG.

## Performance Notes

- Gunicorn workers = 2×CPU+1 guideline (4 default); bump via Helm values.
- Connection pooling via SQLAlchemy `pool_pre_ping`; pgBouncer for >500 conns.
- Redis caches analytics/AI/report renders; CDN caches `/assets` (1 y immutable).
- Report/audit tables: index `created_at`; archive partitions past retention.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| API 503 on boot | DB not ready | entrypoint waits 30×2s; check `db` health |
| Migrations fail | stale `down_revision` chain | `alembic history`, fix chain, re-run Job |
| 401 everywhere | JWT secret rotated | overlap-accept window, re-login |
| Workers idle, queue grows | Redis auth mismatch | compare `REDIS_URL` vs secret |
| TLS errors | cert-manager ClusterIssuer missing | install + `kubectl describe certificate` |
| High latency | cold embedding cache / small pool | warm cache, raise workers/pool size |
