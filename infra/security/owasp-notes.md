# OWASP Top 10 → Controls in This Repo

| Risk | Control |
|---|---|
| A01 Broken Access Control | RBAC service + `require()` on reports/admin; org scoping deps; default-deny NetworkPolicy |
| A02 Cryptographic Failures | TLS 1.2+, HSTS, at-rest encryption (volumes/S3/RDS), KMS rotation, secret manager |
| A03 Injection | SQLAlchemy parameterized queries; AI `SafetyChecker` blocks SQLi/XSS/command injection; pg input via ORM only |
| A04 Insecure Design | Threat-shaped defaults: short JWT life, rate limits, maintenance mode, audit-everything |
| A05 Misconfiguration | Hardened nginx (server_tokens off, secure headers), read-only FS, no debug in prod images |
| A06 Vulnerable Components | Pinned deps, pip-audit + Trivy in CI, weekly scheduled scans |
| A07 Auth Failures | bcrypt/PBKDF2 hashing, login history, suspend/lockout admin actions, MFA status field |
| A08 Data/Software Integrity | Signed GHCR images path (cosign future), Helm `--atomic` deploys, migration Job hooks, hash-chained audit log |
| A09 Logging Failures | Structured JSON logs, correlation IDs, central Prometheus/Grafana, alert rules for auth anomalies |
| A10 SSRF | Egress NetworkPolicy (DNS + intra-namespace only); external API MCP allow-list |
