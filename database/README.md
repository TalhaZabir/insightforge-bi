# Database

## Layout

- `backend/alembic/` — migrations (source of truth for schema).
  - `0001_initial_schema.py` — all tables via `Base.metadata.create_all`
    (models in `backend/app/models/entities.py`).
  - `0002_analytics_views.py` — 7 analytics views (embedded SQL so the
    backend Docker image can migrate without the `database/` folder).
- `database/views/*.sql` — human-readable copies of the same views,
  also used for the Power BI documentation.

## Table groups

Raw ingestion: `uploaded_files`, `import_jobs`, `raw_sales_records`,
`validation_results`, `rejected_records`.
Auth/audit: `users`, `audit_logs`.
Dimensions: `dim_date`, `dim_customer`, `dim_product`, `dim_region`,
`dim_channel`, `dim_sales_rep`.
Fact: `fact_sales` (order-line grain, soft-delete via `is_deleted`,
unique `(batch_id, order_id, line_num)`).

## Views

`v_daily_sales`, `v_monthly_sales`, `v_sales_by_region`,
`v_sales_by_product`, `v_sales_by_category`, `v_sales_by_channel`,
`v_customer_ltv`. All filter `is_deleted = FALSE` and are portable
across PostgreSQL and SQLite.

## Migration workflow

```powershell
cd backend
python -m alembic upgrade head     # migrate
python -m alembic downgrade -1     # roll back one step
python -m alembic revision -m "..."  # new empty revision (edit + fill in)
```

On Docker Compose the backend container runs `alembic upgrade head`
automatically on start.
