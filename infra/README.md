# Infrastructure Map

- `docker/` — backend prod/dev, frontend prod Dockerfiles + entrypoint.
- `compose/` — dev / test / staging / prod stacks.
- `k8s/base/` — plain manifests (namespace → policies → jobs).
- `helm/bi-platform/` — chart + values overlays (dev/staging/prod).
- `terraform/{aws,azure,gcp}/` — per-cloud stacks; `modules/` reserved.
- `nginx/` — reverse proxy, server blocks, frontend static config.
- `monitoring/` — Prometheus scrape config, alert rules, Grafana dashboards.
- `scripts/` — smoke tests, backup/restore, deploy helper, staging certs.
- `security/` — secrets policy, hardening checklist, OWASP mapping.

Deploy order understanding: provision (terraform) → secrets → data services →
`deploy.sh staging` → smoke → promote tag → `deploy.sh prod`.
