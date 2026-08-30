# AI-Powered Business Intelligence and Analytics Platform

A complete enterprise-grade AI-Powered Business Intelligence and Analytics Platform built as a Final Year Bachelor of Engineering Project.

## 📋 Project Status

All phases are complete:

- ✅ **Phase 1** – Software Requirements Specification (SRS)
- ✅ **Phase 2** – Software Architecture & System Design
- ✅ **Phase 3** – Product Design, UX/UI, User Journey & Design System
- ✅ **Phase 4** – PostgreSQL Database Design & Data Modeling
- ✅ **Phase 5** – API Contract Design & Backend Foundation
- ✅ **Phase 6** – Backend Foundation & Core Infrastructure
- ✅ **Phase 7** – Authentication, Authorization, User & Organization Management (IAM)
- ✅ **Phase 8** – Dataset Management & File Storage
- ✅ **Phase 9** – ETL Pipeline, Data Processing & Data Quality Engine
- ✅ **Phase 10** – Business Analytics & KPI Engine
- ✅ **Phase 11** – Dashboard, Visualization & Executive Dashboard Engine

## 📚 Documentation

All design artifacts are in the `docs/` folder:

| Phase | Document |
|------|----------|
| 1 | [Software Requirements Specification](docs/phase1-srs.md) |
| 2 | [Software Architecture](docs/phase2-architecture.md) |
| 3 | [Product Design & UX](docs/phase3-ux-ui.md) |
| 4 | [Database Design](docs/phase4-database.md) |
| 5 | [API Design Specification](docs/phase5-api.md) |
| 6 | [Backend Foundation](docs/phase6-backend-foundation.md) |
| 7 | [IAM Module](docs/phase7-iam.md) (auto‑generated) |
| 8 | [Dataset Management](docs/phase8-dataset.md) (auto‑generated) |
| 9 | [ETL Pipeline](docs/phase9-etl.md) (auto‑generated) |
|10 | [Analytics & KPI Engine](docs/phase10-analytics.md) (auto‑generated) |
|11 | [Dashboard & Visualization](docs/phase11-dashboard.md) (auto‑generated) |

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, TypeScript, TailwindCSS, React Query, React Router, Zustand, Framer Motion, React Hook Form |
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, PostgreSQL, Redis, Celery |
| **ML / AI** | scikit‑learn, statsmodels, TensorFlow / OpenAI LLM placeholder |
| **Charts** | Apache ECharts (primary), Recharts, Chart.js (fallback) |
| **Infra** | Docker, Docker Compose, GitHub Actions, Nginx, SSL (Let's Encrypt) |
| **Storage** | Local (dev), AWS S3 / Azure Blob / GCS (future), MinIO (optional) |
| **Auth** | JWT Access + Refresh Tokens, RBAC, Password bcrypt, Session management |

## 📁 Repository Structure

```
ai-powered-bi-platform/
├─ backend/
│   ├─ app/
│   │   ├─ api/                # FastAPI routers (v1)
│   │   ├─ core/               # Config, security, logger
│   │   ├─ db/                 # SQLAlchemy engine & session
│   │   ├─ iam/                # Authentication & Authorization
│   │   ├─ dataset/            # Upload, metadata, storage abstraction
│   │   ├─ etl/                # Pipeline stages, quality engine, jobs
│   │   ├─ analytics/          # KPI engine, formulas, dashboards
│   │   ├─ dashboard/          # React frontend code (see frontend/)
│   │   ├─ models/             # SQLAlchemy models
│   │   ├─ repositories/       # Repository pattern
│   │   ├─ services/           # Service layer
│   │   ├─ middleware/         # CORS, rate‑limit, security headers
│   │   ├─ dependencies/       # DI (current user, org, db session)
│   │   ├─ cache/              # Redis wrappers
│   │   ├─ storage/            # Storage provider interface
│   │   └─ main.py             # App entry point
│   ├─ migrations/             # Alembic versioned migrations
│   ├─ tests/                  # Pytest suite
│   ├─ docs/                   # Design documents (see root docs/)
│   ├─ pyproject.toml          # Poetry dependency management
│   ├─ Dockerfile
│   └─ docker-compose.yml
├─ frontend/
│   ├─ src/
│   │   ├─ components/         # KPI cards, charts, builder, filters
│   │   ├─ hooks/              # Custom React hooks
│   │   ├─ contexts/           # React contexts (auth, theme, dashboard)
│   │   ├─ pages/              # Dashboard pages, login, etc.
│   │   ├─ router/             # React Router config
│   │   ├─ store/              # Zustand state slices
│   │   ├─ styles/             # Tailwind config, globals
│   │   └─ utils/              # Helpers, constants
│   ├─ public/                 # index.html, favicon
│   ├─ package.json
│   ├─ tailwind.config.js
│   └─ tsconfig.json
├─ docs/
│   ├─ phase1-srs.md
│   ├─ phase2-architecture.md
│   ├─ phase3-ux-ui.md
│   ├─ phase4-database.md
│   ├─ phase5-api.md
│   ├─ phase6-backend-foundation.md
│   ├─ phase7-iam.md
│   ├─ phase8-dataset.md
│   ├─ phase9-etl.md
│   ├─ phase10-analytics.md
│   └─ phase11-dashboard.md
├─ .github/
│   └─ workflows/              # CI/CD (lint, test, docker build, security scan)
├─ .env.example
├─ .gitignore
└─ README.md
```

## 🚀 Getting Started

```bash
# Clone the repo
git clone https://github.com/DEBEYENDU/ai-powered-bi-platform.git
cd ai-powered-bi-platform

# Backend
cd backend
poetry install          # installs Python deps
cp .env.example .env    # edit with your DB/Redis/JWT secrets
poetry run alembic upgrade head   # run migrations
uvicorn app.main:app --reload     # start API (http://127.0.0.1:8000)

# Frontend
cd ../frontend
npm install
npm run dev               # Vite dev server (http://localhost:5173)

# Docker (all services)
docker compose up --build   # starts API, DB, Redis, Celery worker
```

## 👥 Team

- **Girme Prachi Mahadu** – Project Lead / Requirements
- **Nalawade Tanuja Chandrakant** – Architecture & Backend
- **Pande Sanjana Santosh** – Database & ETL
- **Patil Sanjivani Lahuraj** – Frontend & UI/UX

**Guide:** Prof. K. N. Agalave, SPVP’s S.B. Patil College of Engineering, Indapur

## 📄 License

Academic project – SPVP’s SBCPOE, Indapur. No commercial use without permission.

## 📫 Contact

For questions or contribution, please open an issue on the GitHub repository or contact the project maintainers.

---

*Generated on 2026‑08‑31. This README reflects the completion of all 11 project phases.*