# CI/CD & Pipeline Audit Report

Date: 2026-09-04. Scope: all 4 workflows, Dockerfiles, compose files, deps,
tests, env config. Method: reproduced locally (Python 3.14, Node 24, ruff,
pytest, full `pip install -r backend/requirements.txt`, `npm run build`).

## 1. Issues found and fixes

### A. Integration job could never run tests (CI, critical)
- **Why:** `integration-test` installed only `backend/requirements.txt`, which
  contains no pytest. `python -m pytest` → `ModuleNotFoundError`.
- **Fix:** install `pytest pytest-asyncio httpx` in the job (`ci.yml`).
- **Also:** dropped the now-obsolete `--ignore=backend/app/ai/tests` (those
  tests are fixed, see C) and added a boot smoke step
  (`python -c "from app.main import app"`) so broken router wiring fails fast.

### B. `helm lint` fails without chart dependencies (CI build, high)
- **Why:** chart depends on Bitnami postgres/redis subcharts absent from the
  repo; `helm lint` errors before checking anything.
- **Fix:** `helm dependency update` step before lint in `ci.yml`.

### C. All AI tests failed at collection (tests, critical)
- **Why:** `app/ai/__init__.py` chain imports `app.ai.schemas.citation` and
  `app.ai.schemas.chat`, which did not exist as modules.
- **Fix:** created `backend/app/ai/schemas/citation.py` + `chat.py` re-exporting
  the canonical models from `app.ai.tools.schemas` (no duplication).

### D. Two genuine test failures (tests, medium)
- `test_business_context`: test calls `add_business_context(..., org_id=...)`
  but the method took `organization_id`. Renamed the parameter (sole caller).
- `test_detect_root_cause`: "Why did sales decrease?" tied 1–1 and lost to
  dict order. Scoring now weights matches by pattern length (specificity), so
  question phrases outrank generic keywords.

### E. SARIF upload rejected (Security, high)
- **Why:** `upload-sarif` needs `security-events: write`; the job had no
  `permissions:` block (defaults are read-only).
- **Fix:** added `permissions: { contents: read, security-events: write }`.

### F. CD deployed into clusters that do not exist (CD, high)
- **Why:** `helm upgrade` + `kubectl rollout status` with no kubeconfig/cluster
  fail on every push. Faking success would violate policy; deleting the
  workflows would lose the delivery path.
- **Fix:** both CD workflows now do everything real that needs no cluster
  (build+push images, `helm template --validate` manifest rendering) on their
  normal triggers; the cluster `deploy`/`smoke`/`rollback` jobs run only on
  `workflow_dispatch` behind environment protection + kubeconfig secrets, with
  the reason documented in workflow comments.

### G. App could not boot: wrong import paths (backend, critical)
- **Why:** Phase 7–10 files used `from analytics...` (top-level package that
  does not exist) instead of `from app.analytics...`; `analytics/cache.py`
  imported `analytics.core.config` (nonexistent); `etl/stages/*` missed the
  `PipelineStage` import; `auth_service.py` missed `uuid` + `User`.
- **Fix:** corrected all paths, rewrote `analytics/cache.py` onto
  `app.core.config` with lazy client creation. Verified: `from app.main import
  app` assembles 193 OpenAPI paths.

### H. Missing runtime dependencies (backend, high)
- `EmailStr` (IAM schemas) without `email-validator` → import crash at boot.
  Added to `requirements.txt` + `pyproject.toml`.
- `aiofiles`/`chardet` (ETL extract stage) absent from both manifests. Added.

### I. Unbounded DB connects hang workers + health checks (backend, high)
- **Why:** `create_engine` had no `connect_timeout`; psycopg blocked
  indefinitely (reproduced: full suite hung; faulthandler pinned
  `psycopg/waiting.py`). Same risk class for Celery inspect.
- **Fix:** `connect_args={"connect_timeout": 5}` for postgresql URLs;
  `inspect(timeout=2.0)`. Health suite now degrades in bounded time.

### J. Lint gate was decorative (CI, medium)
- **Why:** `ruff check ... || true` always green; actual state was 1632
  violations.
- **Fix:** 1444 auto-fixed, rest triaged honestly: B008 (FastAPI idiom),
  DTZ (naive-UTC convention), RUF012 (Pydantic-safe), UP042/UP046 documented
  ignores; BLE001 narrowed to `ImportError` for pure fallbacks or
  per-file-ignored where broad catching is the design (probes, fan-out);
  B904/SIM/F841/B905/S108/S110/S112/RUF001/RUF059/S701 fixed in code;
  S701 fixed by enabling Jinja autoescape. `ruff check` + `ruff format --check`
  now pass clean and the `|| true` bypasses are removed.

### K. No frontend coverage in CI (CI, medium)
- Verified `npm run build` passes locally; added a `frontend` CI job
  (Node 20, npm cache, `npm ci`, `npm run build`). Committed the generated
  `frontend/package-lock.json` for deterministic installs.

### L. Fragile test-compose wiring (infra, low)
- `infra/compose/test.yml` mounted scripts to a `..`-traversal path and ran
  pytest without installing it. Simplified to `/scripts` mount + pip install
  in the test command.

### M. Missing dependency automation (process, low)
- Added `.github/dependabot.yml` (pip/npm/docker/actions, weekly).

## 2. Files changed
- `.github/workflows/ci.yml, security.yml, cd-staging.yml, cd-prod.yml`,
  `.github/dependabot.yml` (new)
- `backend/requirements.txt`, `backend/pyproject.toml` (deps + ruff policy)
- `backend/app/ai/schemas/{citation,chat}.py` (new), `memory.py`,
  `orchestrator/intent_detector.py`, `tools/{dashboard,ml,report}_tools.py`,
  `analytics/{cache,routers/analytics,schemas/kpi,kpi/calculators/*}`,
  `etl/stages/*`, `iam/services/auth_service.py`, `db/session.py`,
  `core/security.py`, admin/reports services (suppress/B904), frontend lockfile
- `infra/compose/test.yml`; ~130 files touched by ruff modernization+format

## 3. Remaining warnings (accepted, with reason)
- Pydantic v1 `@validator` deprecation warnings in AI schemas (work, migrate later).
- `datetime.utcnow()` DeprecationWarnings on 3.14 (naive-UTC convention kept).
- pip-audit stays non-blocking by policy (weekly triage, App. Security flow).
- Helm templates validated by `helm lint/template` in CI, not plain YAML parse.
- mypy not gated: codebase-wide strict typing is a later phase (see below).

## 4. Required secrets (documented, none hardcoded)
- CI/CD: `GITHUB_TOKEN` (auto), `STAGING_KUBECONFIG`, `STAGING_JWT_SECRET`,
  `PROD_KUBECONFIG`, `PROD_JWT_SECRET` (only needed when clusters exist).
- Compose prod: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `JWT_SECRET_KEY`,
  `GRAFANA_PASSWORD`, `REGISTRY`, `TAG`.

## 5. Recommended next improvements
1. ~~Gate mypy incrementally~~ DONE (pass 2): foundation layer gated.
2. Coverage thresholds (`--cov-fail-under`) once suite grows.
3. Pin action SHAs for supply-chain hardening.
4. Provision staging cluster → flip CD deploy to automatic.
5. Migrate `@validator` → `@field_validator`, naive → aware datetimes (major).

---

# Pass 2 audit (2026-09-05): action currency, least privilege, type gates

## N. End-of-life actions would have failed imminently (all workflows, critical)
- Verified against upstream READMEs/releases: GitHub removed Node 20 from
  runners — **gitleaks-action@v2 stops working entirely**; v3 (Node 24) is the
  supported line and additionally requires `GITHUB_TOKEN` for PR scans.
- Bumped with verification, not blindly:
  `actions/checkout@v4→v7`, `actions/setup-python@v5→v7`,
  `actions/setup-node@v4→v7` (all Node 24 per upstream docs),
  `azure/setup-helm@v4→v5` (upstream README), `gitleaks@v2→v3` (+ `GITHUB_TOKEN`
  env, `contents:read` + `pull-requests:read`), `upload-sarif@v3→v4`
  (v4 is latest; v3 still supported), `trivy-action@0.24.0→0.36.0` (latest).
  Docker-based actions (`build-push@v6`, `login@v3`) are unaffected by the
  Node deprecation and already current — left pinned.
- Node runtime 20→24 in CI (`NODE_VERSION`) and `frontend.prod.Dockerfile`
  (Node 20 went EOL April 2026). Local `npm run build` + `npm test` verified
  on Node 24. Python stays 3.12 (matches prod image + `requires-python`).

## O. Workflows ran with implicit token permissions (all, medium)
- Added explicit least-privilege blocks: CI top-level `contents: read`;
  per-job `contents: read` on CD render/deploy/smoke/rollback;
  `security-events: write` only on the SARIF-upload job. Gitleaks got exactly
  `contents: read` + `pull-requests: read` per its docs.

## P. No type checking in CI (CI, medium)
- Measured first: `app/core` + `app/db` were already clean, then the whole
  foundation layer (24 files). Added `[tool.mypy]` (namespace-package flags
  included) and a CI `typecheck` job gated to that scope; feature modules
  onboard incrementally (`follow_imports = skip`).

## Q. No frontend tests existed (CI, medium)
- Added vitest + jsdom + Testing Library, `vitest.config.ts`, hermetic
  `App.test.tsx` (API mocked, asserts nav renders), `npm test` script, and a
  CI step. Fixed two real setup bugs found while doing it (jest-dom v7 needs
  `globals: true`; matchers need the `/vitest` setup entry).

## Verification (pass 2)
- `ruff check` + `ruff format --check`: clean. `mypy`: 24 files clean.
- Backend 55/55 pass; frontend `npm test` 1/1 + `npm run build` pass;
  `npm audit --audit-level=high`: 0 vulnerabilities.
- 9/9 workflow+compose YAML files parse. Dependabot covers pip/npm/docker/actions.
