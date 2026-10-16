# Security considerations

- Secrets only via env (`JWT_SECRET`, `POSTGRES_PASSWORD`); `.env.example`
  ships placeholders; `.env` is git-ignored.
- Passwords hashed with bcrypt (direct library use — passlib removed for the
  bcrypt-4 incompatibility); JWT HS256, 60-min expiry; no stack traces or
  secret values in responses/logs.
- Uploads: extension + MIME allowlist, 25 MB cap enforced while streaming,
  filename sanitized (`basename` + char allowlist, UUID prefix → no path
  traversal), stored under `./uploads` (never served), SHA256 dedup.
- SQL: SQLAlchemy throughout (parameterized); no string-built queries.
- AuthZ on every protected route (`require_role`); viewer uploads → 403
  (tested); CORS allowlist; secure-cookie guidance for same-domain deploys
  in `docs/deployment.md`.
- Audit: `audit_logs` rows for login/logout/upload/validate/clean/
  confirm-start/confirm/cancel/discard/export.
- Rate limiting: login capped at 10/min (slowapi); upload throttling via
  size cap + authenticated-only uploads.
