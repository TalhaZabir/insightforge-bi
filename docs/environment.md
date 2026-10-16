# Environment variables

| Name | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes (prod) | `sqlite:///./insightforge.db` | SQLAlchemy URL. Compose sets Postgres. |
| `POSTGRES_USER/PASSWORD/DB` | compose | `insightforge/...` | Postgres service credentials |
| `JWT_SECRET` | **yes** | `change-me-...` | HS256 signing key (≥32 random chars in prod) |
| `JWT_ALGORITHM` | no | `HS256` | Token algorithm |
| `JWT_EXPIRE_MINUTES` | no | `60` | Access-token lifetime |
| `CORS_ORIGINS` | no | `http://localhost:3000` | Comma-separated allowlist |
| `MAX_UPLOAD_MB` | no | `25` | Upload size cap |
| `UPLOAD_DIR` | no | `./uploads` | Storage outside served dirs |
| `LOG_LEVEL` | no | `INFO` | `DEBUG/INFO/WARNING/ERROR` |
| `BACKEND_PORT` | no | `8000` | Compose host mapping |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` | Baked into the frontend build |

Rules: never commit `.env`; validate on boot via `pydantic-settings`
(missing/invalid values fail fast); no secret is ever logged
(see `docs/security.md`).
