# Secrets Management

## Rules (non-negotiable)

1. No secrets in source code, images, or chat logs. Gitleaks runs on every push.
2. Local/dev only: `backend/.env` (git-ignored) copied from `.env.example`.
3. Compose staging/prod: environment variables from a vault-injected env file.
4. Kubernetes: Sealed Secrets or External Secrets (Secrets Manager / Key Vault /
   GCP Secret Manager) — `infra/k8s/base/secrets.yaml` holds placeholders only.
5. Terraform: remote state with encryption; DB passwords go straight to the
   cloud secret manager (see per-cloud outputs), never to outputs in plain text.

## Rotation

- JWT secret: rotate via overlapping acceptance — deploy new secret as
  `JWT_SECRET_KEY_NEXT`, accept both for one access-token lifetime (15 min),
  then promote. Token lifetimes are short by design.
- DB/Redis passwords: rotate in secret manager → rolling restart of
  deployments (zero-downtime via `maxUnavailable: 0`).
- KMS data keys: 90-day rotation (`rotation_period` in GCP stack).

## Access & audit

- Least privilege: only api/worker/scheduler service accounts read app secrets.
- Every secret read in-cluster is logged via Kubernetes audit policy.
- Admin settings changes and flag kills are recorded in the app audit log
  (`/admin/audit`) with hash-chain verification.
