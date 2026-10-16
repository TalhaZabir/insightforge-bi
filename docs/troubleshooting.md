# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `alembic` says “Path doesn't exist: alembic” | Run from `backend/` (script paths are relative) |
| `/readiness` → `not_ready` | Postgres down or `DATABASE_URL` wrong; check `docker compose ps` |
| `409 Duplicate of previously uploaded file` | Same SHA256 already imported — intentional; check history |
| `422 mapping_problems` | Required field unmapped — map it in the wizard |
| Job stuck `processing` | Loader exception → status becomes `failed` with class name; check backend logs (`X-Request-ID`) and retry |
| Login 401 with seed creds | Seeds not run: `python -m app.seeds.run` (from `backend/`) |
| Frontend `npm run` breaks | Spaces in folder path break `.cmd` shims — use `node ./node_modules/...` directly or rename folder (see `docs/setup.md`) |
| Empty dashboards | No confirmed import, or filters exclude everything — clear filters / check Data Imports history |
| `bcrypt`/`passlib` errors | `passlib` was removed in Part 3 — `pip install -r requirements.txt` fresh |
| psycopg2 missing locally | Only needed for Postgres; SQLite fallback needs nothing |
