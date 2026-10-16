# API usage

OpenAPI: `http://localhost:8000/docs`. Auth: `Authorization: Bearer <JWT>`
from `POST /auth/login`. Errors are `{detail: ...}` with proper codes
(400/401/403/404/409/413/422); every response carries `X-Request-ID`.

| Method & path | Role | Notes |
|---|---|---|
| `POST /auth/login` | public (10/min) | `{email, password}` → `{access_token}` |
| `POST /auth/logout` · `GET /auth/me` · `GET /auth/users` | user · user · admin | |
| `POST /uploads` (multipart) | admin/analyst | ext+MIME+25 MB+SHA256-dedup (409) |
| `GET /uploads` · `GET /uploads/{id}` · `DELETE /uploads/{id}` | user · user · admin | history; `?force=true` also deletes confirmed `fact_sales` (blocked while `processing`) |
| `POST /uploads/{id}/preview` | user | `{sheet?, limit}` + alias suggestions |
| `POST /uploads/{id}/validate` | admin/analyst | `{sheet, mapping}` → job + summary (422 on bad mapping) |
| `POST /uploads/{id}/clean` | admin/analyst | `{job_id}` → transformations + examples |
| `POST /uploads/{id}/confirm` | admin/analyst | `{job_id}` → `processing` (background load) |
| `GET /imports/{id}/status` · `POST /imports/{id}/cancel` | user · admin/analyst | poll until `confirmed`/`failed` |
| `GET /data-quality/{job}` · `.../rejections.csv` | user | report + download |
| `GET /analytics/overview\|sales\|profitability\|customers\|products\|regions` | user | shared filters; `GET /analytics/sales/orders` paginated |
| `GET /analytics/facets` | user | distinct filter values |
| `GET /insights` | user | traceable insight list |
| `GET /exports/power-bi` | any role | ZIP bundle (audited) |
| `GET /health` · `GET /readiness` | public | liveness vs DB readiness |
