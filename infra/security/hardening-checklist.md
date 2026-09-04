# Production Hardening Checklist

## Containers
- [ ] Images built from pinned digests in release pipeline
- [ ] Multi-stage builds; no build tools in runtime image
- [ ] Non-root users (appuser 10001, static 10002)
- [ ] readOnlyRootFilesystem + dropped capabilities (k8s manifests)
- [ ] seccomp RuntimeDefault profile
- [ ] HEALTHCHECK on all images
- [ ] Trivy scan gates merges (`.github/workflows/security.yml`)

## Network
- [ ] TLS 1.2+ only, HSTS preload, strong ciphers (nginx.conf)
- [ ] HTTP→HTTPS redirect; ACME challenge path open
- [ ] Default-deny NetworkPolicy + explicit allows (k8s/policies.yaml)
- [ ] Rate limits: 100r/m API, 10r/m auth endpoints
- [ ] CORS restricted to app origins (no `*` in prod)

## Application
- [ ] JWT_SECRET_KEY ≥ 32 chars from secret manager (never default)
- [ ] Short-lived access tokens (15 min) + refresh rotation
- [ ] RBAC enforced on all mutating routes; org isolation
- [ ] Maintenance middleware active; override tokens minted per-incident
- [ ] Structured JSON logs with correlation IDs; PII masked (AI safety layer)

## Data
- [ ] Encrypted volumes (storage + backups), S3 SSE + versioning
- [ ] Daily backups + 14-day retention + verified restores (quarterly DR drill)
- [ ] `alembic upgrade head` runs before traffic (entrypoint/Job hook)

## Operations
- [ ] Prometheus + Grafana + alerts deployed; alertmanager routed
- [ ] PDBs respected during node drains; HPA min replicas ≥ 2 (prod)
- [ ] Rollback tested: `helm rollback` and compose previous TAG
