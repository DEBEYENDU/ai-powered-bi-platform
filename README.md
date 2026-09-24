# AI-Powered Business Intelligence Platform

**Version 1.0.0** — Final Product Release

A complete enterprise-grade, multi-tenant AI-powered Business Intelligence and Analytics Platform with Natural Language querying, autonomous AI agents, RAG, MLOps, workflow automation, and governance.

## Core Capabilities

| Category | Features |
|----------|----------|
| **Data** | Dataset upload (CSV/Excel/JSON/Parquet), profiling, quality scoring, ETL pipelines, data cleaning, transforms |
| **Analytics** | SQL queries, Natural Language to SQL (NLQ), KPI engine, business analyst AI, forecasting, scenario analysis |
| **Visualization** | Interactive dashboards, chart generation, AI-powered dashboard creation |
| **AI** | AI Chat, business analyst, report generation, copilot, multi-agent orchestration, autonomous task execution |
| **Knowledge** | Document upload, RAG (Retrieval-Augmented Generation), semantic search, collections, citation tracking |
| **Reporting** | Template-based reports, scheduled generation, PDF/DOCX/XLSX/PPTX export, version history, approval workflows |
| **Workflows** | Visual workflow builder, approval chains, trigger system, execution history, templates |
| **MLOps** | Model registry, experiments, training runs, deployments, drift detection, monitoring |
| **Governance** | Security classifications, retention policies, access reviews, compliance policies |
| **Multi-Tenant** | Organization isolation, plans (Free/Starter/Pro/Enterprise), quotas, usage metering, API keys |
| **Security** | JWT auth, RBAC, tenant isolation, rate limiting, path traversal protection, SQL injection protection |
| **Operations** | Audit logging, metrics, alerts, health checks, Docker, CI/CD |

## Architecture

```text
                    ┌─────────────────┐
                    │   React + Vite   │  Frontend (65 pages)
                    │   TypeScript     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     FastAPI      │  Backend (Python 3.14)
                    │   SQLAlchemy     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────┐    ┌───────▼──────┐    ┌───────▼──────┐
│  PostgreSQL   │    │    Redis     │    │    Storage    │
│  (database)   │    │  (cache)     │    │  (files)     │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Backend Modules

| Module | Location | Purpose |
|--------|----------|---------|
| IAM | `app/iam/` | Authentication, users, organizations, plans, quotas, API keys |
| Dataset | `app/dataset/` | Upload, profile, store datasets |
| ETL | `app/etl/` | Data processing pipelines |
| Analytics | `app/analytics/` | KPI engine, formulas |
| AI | `app/ai/` | Chat, NLQ, business analyst, dashboard gen, reports, copilot |
| Knowledge | `app/knowledge/` | Documents, collections, RAG, search |
| Reports | `app/reports/` | Template reports, scheduling, export |
| Workflows | `app/workflows/` | Workflow builder, executions, approvals |
| MLOps | `app/mlops/` | Models, experiments, training, deployments, monitoring |
| Governance | `app/governance/` | Policies, classifications, retention, security |
| Admin | `app/admin/` | Platform administration, RBAC, feature flags, metrics |
| Storage | `app/storage/` | Tenant-isolated file storage, object storage abstraction |

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # Linux/Mac

pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL, Redis URL, and JWT secret

# Generate a secure JWT secret:
python -c "import secrets; print(secrets.token_hex(32))"

# Run migrations
python -m alembic upgrade head

# Start server
uvicorn app.main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Frontend at http://localhost:5173
```

### Docker

```bash
docker compose up --build
# Starts API, PostgreSQL, Redis, Celery worker
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | `development` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://bi:bi@localhost:5432/bi_platform` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | JWT signing secret (MUST change in production) | `change-me-in-production` |
| `STORAGE_PATH` | File storage directory | `./storage` |
| `REPORTS_PATH` | Report storage directory | `./reports` |
| `AI_PROVIDER` | AI provider (openai/ollama/azure) | `openai` |
| `AI_MODEL` | AI model name | `gpt-4o-mini` |
| `OPENAI_API_KEY` | OpenAI API key | (empty) |
| `RATE_LIMIT_PER Minute` | API rate limit per minute | `120` |

## Multi-Tenancy

The platform is fully multi-tenant with Organization as the canonical tenant boundary.

### Plans

| Plan | Users | Datasets | Storage | AI Requests | Price |
|------|-------|----------|---------|-------------|-------|
| Free | 3 | 5 | 100 MB | 50/month | $0 |
| Starter | 10 | 25 | 1 GB | 200/month | $29/mo |
| Professional | 50 | 100 | 10 GB | 1000/month | $99/mo |
| Enterprise | Unlimited | Unlimited | Unlimited | Unlimited | $499/mo |

### Tenant Isolation

- **Database**: All queries scoped by `organization_id`
- **Storage**: Files under `storage/tenants/{tenant_id}/`
- **Cache**: Redis keys prefixed with `t:{tenant_id}:`
- **Rate Limiting**: Per-tenant rate limits with suspended tenant blocking
- **RAG**: Documents and embeddings scoped per tenant
- **AI**: Context restricted to tenant's own data
- **Workflows**: Executions bound to tenant
- **MLOps**: Models and experiments scoped per tenant

## Testing

```bash
# Backend tests
cd backend
python -m pytest app/ -v

# Frontend type check
cd frontend
npx tsc --noEmit
```

## Security

- JWT authentication with configurable expiry
- RBAC with 4 roles: superadmin, org_admin, analyst, viewer
- Tenant isolation enforced at database, storage, cache, and API layers
- SQL injection protection via SQLValidator
- Path traversal protection via validate_storage_path
- Rate limiting per tenant with Redis-backed sliding window
- API key authentication for service-to-service calls
- Startup validation rejects insecure JWT secrets in production
- pip-audit enforced in CI (blocking, not advisory)
- Non-root Docker execution
- No hardcoded secrets in codebase

## Database Migrations

```bash
cd backend
python -m alembic upgrade head     # Apply all migrations
python -m alembic current          # Check current version
python -m alembic history          # View migration history
```

17 migrations from initial schema through multi-tenant infrastructure.

## CI/CD

GitHub Actions workflows:
- `ci.yml` — Backend tests, lint, TypeScript check, frontend build
- `security.yml` — Secret scanning (gitleaks), dependency audit (pip-audit), container scanning (Trivy)
- `cd-staging.yml` — Staging deployment
- `cd-prod.yml` — Production deployment

## API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, MUI v9, Vite, React Router |
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.x, Pydantic v2 |
| Database | PostgreSQL 15+ with Alembic migrations |
| Cache | Redis 7+ with in-memory fallback |
| AI | OpenAI / Ollama / Azure OpenAI / Gemini / Anthropic |
| ML | scikit-learn, statsmodels |
| Charts | Apache ECharts, Recharts |
| Auth | JWT, bcrypt, RBAC |
| Storage | Local filesystem (cloud-ready abstraction) |
| Infra | Docker, GitHub Actions |
| Testing | pytest, TypeScript |

## License

Academic project — SPVP's SBCPOE, Indapur. No commercial use without permission.
