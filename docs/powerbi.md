# Power BI connection guide

Full model reference: `database/powerbi_model.md`. Measures:
`database/dax/measures.dax` (18 measures, matching `docs/analytics.md`).

## Option A — Import (no DB access needed)

1. In the app: **Power BI Export → Download bundle (.zip)**.
2. Extract; Power BI Desktop → Get Data → Text/CSV → load all 7 files.
3. Model view → create relationships (Many-to-One, single direction):
   `fact_sales[customer_key]→dim_customer[id]`,
   `[product_key]→dim_product[id]`, `[region_key]→dim_region[id]`,
   `[channel_key]→dim_channel[id]`, `[rep_key]→dim_sales_rep[id]`,
   `[date_key]→dim_date[date_key]`.
4. New measures table → paste `measures.dax`.
5. Slicer default: exclude `Cancelled` in `fact_sales[order_status]`.

## Option B — DirectQuery (always fresh)

Get Data → PostgreSQL → host/port/db from `.env` → paste the view
definitions from `database/views/*.sql` (run once in the DB), connect the
same relationships against the views, mark `dim_date[date]` as the date
table for time intelligence.
