# Deployment

## Oracle Cloud Always Free VM (Production)

Full automated setup with Nginx reverse proxy, host firewall automation, and Always Free VM creation walkthrough:
👉 See [docs/oracle-cloud-deployment.md](file:///f:/End-to-End%20Business%20Intelligence%20&%20Analytics%20Platform/docs/oracle-cloud-deployment.md)

Quick deploy on an Oracle VM:
```bash
sudo bash scripts/setup-oracle-vm.sh
```

## Docker Compose (any host with Docker)

```bash
cp .env.example .env   # set JWT_SECRET, POSTGRES_PASSWORD
docker compose up --build -d
```

Postgres persists in the `pgdata` volume; the backend migrates on boot.
Back up with `docker compose exec postgres pg_dump -U insightforge insightforge > backup.sql`.

## Render

- New **PostgreSQL** service; new **Web Service** from `backend/` Dockerfile,
  start command already migrates (`alembic upgrade head && uvicorn ...`);
  set `DATABASE_URL` to Render's internal URL, plus `JWT_SECRET`, `CORS_ORIGINS`.
- New **Static Site** from `frontend/` (`npm run build`), env
  `NEXT_PUBLIC_API_URL=<backend URL>`.

## Railway / Fly.io

Same shape: managed Postgres + backend container + frontend static/build.
`DATABASE_URL` is the only DB wiring; migrations run at container start.
No cloud credentials live in the repo — everything is env-driven.

## Production checklist

`JWT_SECRET` ≥ 32 random chars · `CORS_ORIGINS` set to the real frontend ·
`LOG_LEVEL=INFO` · Postgres backups scheduled · demo passwords rotated ·
`/readiness` wired to the platform health check.
