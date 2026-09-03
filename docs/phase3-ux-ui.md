# Phase 3 – Product Design & UX/UI

> **Implementation Status (as of 2026-09-03):** Design specification complete.
> **No frontend code exists yet** (no `frontend/` directory). The AI Assistant API
> (`POST /ai/chat`, `POST /ai/nlq`) is implemented and ready for UI integration.

## Design Principles

Simplicity, Minimalism, Enterprise-grade, Consistency, Accessibility WCAG 2.1 AA,
Mobile-first.

## User Personas

Administrator, Business Owner, Business Analyst, Data Analyst, Manager, Viewer.

## User Journey (Designed)

Register → Verify → Login → Create Org → Upload Dataset → Validate → Dashboard →
Forecast → AI Chat → Export Report.

Backend support per step:

| Journey Step | Backend Support | UI |
|---|---|---|
| Register / Login | ✅ `/auth/register`, `/auth/login` | ❌ Missing |
| Upload Dataset | ✅ `/datasets/` + upload/preview | ❌ Missing |
| Validate (ETL) | ✅ `/etl/jobs` | ❌ Missing |
| Dashboard | ❌ No dashboard backend | ❌ Missing |
| Forecast | ⚠️ Placeholder forecast tools | ❌ Missing |
| AI Chat | ✅ `/ai/chat`, `/ai/nlq` | ❌ Missing |
| Export Report | ⚠️ Report tool skeleton | ❌ Missing |

## Information Architecture (Planned Sidebar)

Dashboard, Datasets, Analytics, Predictions, AI Assistant, Reports, Organization, Settings.

## Design System

Typography Inter, Spacing 4px grid, Primary Indigo, Color tokens.
Components: Button, Input, Card, Table, Chart, Dialog.

Planned stack (per README): React 19, TypeScript, TailwindCSS, React Query, React Router,
Zustand, Framer Motion, React Hook Form. Charts: Apache ECharts (primary), Recharts/Chart.js fallback.

## Dashboard Design (Spec)

Executive Dashboard with KPI cards, AI Insight Panel, Sales Trend, Top Products, Geo Map.
`GET /ai` dashboard-summary tools exist server-side; widgets/UI not built.

## Accessibility & Responsive (Requirements for Build)

Keyboard nav, focus management, Desktop/Tablet/Mobile layouts, WCAG 2.1 AA.

## Next Steps

1. Scaffold `frontend/` (Vite + React + TS + Tailwind) per stack above.
2. Build Auth → Datasets → AI Chat pages first (backend already supports them).
3. Add Dashboard/Analytics pages once Phase 11–12 backends land.
