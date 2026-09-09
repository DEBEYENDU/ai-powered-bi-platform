# BI Platform Launcher

Windows desktop control plane for the AI-Powered BI Platform. One window to
start, stop, monitor, and manage backend + frontend + dependencies — no
terminals needed.

## Run from source

```powershell
cd launcher
pip install -r requirements.txt
python main.py
```

The launcher auto-detects the project root (its own parent directory), so it
also works with `python launcher\main.py --root <path>`.

## Build the executable

```powershell
cd launcher
pip install pyinstaller
python build_exe.py
```

Output: `launcher\dist\BI Platform Launcher.exe`. Double-click to run. For a
portable setup, place the exe in the project root next to `backend/` and
`frontend/` (it resolves the root from its own location).

## What Start Project does

1. Detects Python / Node.js / npm (versions logged, friendly errors).
2. Checks PostgreSQL (warns only) and Redis (starts `bi-redis` container via
   Docker when available, warns otherwise — the app degrades gracefully).
3. Creates `backend/.env` from `.env.example` if missing.
4. Creates storage/reports folders.
5. Runs `npm install` only when `node_modules` is missing.
6. Starts the backend with `backend/.venv` when present (falls back to the
   current interpreter with a logged warning).
7. Waits for `/health`, then starts the frontend and waits for it.
8. Opens `http://localhost:5173` (configurable).

## Panels

- **Status**: Backend, Frontend, Database, Redis, Storage, Health,
  Maintenance mode, CPU, Memory, Disk (green/yellow/red).
- **Health**: per-service status, latency, details; refreshes every 5s.
- **System**: CPU/memory bars, sparkline graphs, backend/frontend uptime.
- **Logs**: live tabs per service with search, copy, save, auto-scroll.
- **Settings** (`launcher_config.json`): ports, DB/Redis URLs, storage paths,
  theme, auto-open browser, Redis container management.

## Notes

- Closing the window minimizes to the system tray (double-click restores).
- Logs persist under `launcher/logs/`.
- Stop kills managed processes plus stray uvicorn/vite orphans.
- Git branch/commit/version shown in the sidebar (when run inside the repo).
