# BI Platform — Administration Dashboard

React 19 + TypeScript + React Router admin portal for the Phase 15 backend
(`/api/v1/admin`). No chart dependencies — status is rendered with text and
color so the bundle stays lean; plug ECharts in later for metrics graphs.

## Run

```bash
npm install
npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

Set `localStorage.bi_token` to a JWT access token to call authenticated routes.

## Pages

Overview, Users, Organizations, Roles, Health, Metrics, Audit, Alerts, Jobs,
Flags, Settings — each maps 1:1 to backend `/admin` endpoints.
