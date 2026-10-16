# Architecture

```
browser ─▶ Next.js 14 (App Router, client components + Recharts)
        ─▶ FastAPI (/health, /auth, /uploads, /analytics, /insights, /exports)
        ─▶ PostgreSQL 16 (raw zone + star schema + SQL views)
```

- **Frontend** (`frontend/`): TypeScript, Tailwind, shadcn-style primitives,
  React Hook Form + Zod, TanStack Query. Auth token in `localStorage`;
  `AuthGuard` redirects 401 → `/login`, 403 → `/forbidden`.
- **Backend** (`backend/app/`): `api/` routes, `auth/` (bcrypt + JWT),
  `ingestion/` (parser → mapper → validator → cleaner → loader),
  `analytics/` (shared filters + SQL aggregates), `insights/` (deterministic
  rules), `exports/` (Power BI ZIP). Request-ID middleware, structured JSON
  logs, CORS allowlist, slowapi rate limit on login (10/min).
- **Database**: raw ingestion tables, 6 dimensions + `fact_sales`
  (order-line grain, soft delete), 7 analytics views via Alembic.
- **Background work**: FastAPI `BackgroundTasks` for the confirm/load step;
  the job row (`processing → confirmed/failed`) is the status channel —
  no Redis/Celery by design (see `docs/limitations.md`).
