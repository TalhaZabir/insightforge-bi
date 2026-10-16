# InsightForge BI — Power BI data model

## Star schema

```
dim_date ──────┐
dim_customer ──┤
dim_product ───┼──▶ fact_sales (one row per order line)
dim_region ────┤
dim_channel ───┤
dim_sales_rep ─┘
```

All relationships: **Many (fact) → One (dimension), single direction**.
Join keys: `*_key` = dimension `id`, except `date_key` (YYYYMMDD) = `dim_date[date_key]`.

## Field definitions

| Table | Key fields | Notes |
|---|---|---|
| `fact_sales` | `order_id`, `date_key`, `customer_key`, `product_key`, `region_key`, `channel_key`, `rep_key`, `quantity`, `unit_price`, `discount` (0–1), `cost` (unit), `shipping_cost`, `revenue`, `profit`, `payment_method`, `order_status`, `batch_id` | `profit = revenue − cost×qty − shipping` |
| `dim_date` | `date_key`, `date`, `year`, `quarter`, `month`, `weekday`, `is_weekend` | Continuous calendar, pre-seeded 2023–2026 |
| `dim_customer` | `customer_id` (natural), `customer_name`, `segment` | Consumer / SMB / Enterprise |
| `dim_product` | `product_id`, `product_name`, `category`, `subcategory` | 5 categories in demo data |
| `dim_region` | `region`, `country` | |
| `dim_channel` | `channel` | Online / Retail Store / Wholesale |
| `dim_sales_rep` | `rep_name` | |

SQL views with identical grain live in `database/views/*.sql`
(`v_daily_sales`, `v_monthly_sales`, `v_sales_by_region`,
`v_sales_by_product`, `v_sales_by_category`, `v_sales_by_channel`,
`v_customer_ltv`). DAX measures in `database/dax/measures.dax` match the
app's SQL definitions (see `docs/analytics.md` for the cancelled-order rule
and the prev-equivalent-period growth definition).

## Import mode vs DirectQuery

- **Import (recommended):** download the ZIP from Power BI Export, load the
  7 CSVs, build the relationships above, paste the DAX measures. Fast,
  scheduled-refresh friendly, works without DB access.
- **DirectQuery:** point Power BI at PostgreSQL (`Get Data → PostgreSQL`),
  import the `database/views/*.sql` views instead of raw tables. Always
  fresh; slower for large models and time-intelligence needs a marked date
  table (`dim_date[date]`).

## Example dashboard layout (matches the app)

1. **KPI row:** Cards for Total Revenue, Total Profit, Profit Margin,
   Total Orders, Average Order Value (all with Revenue/Profit Growth %).
2. **Trend:** Line chart, `dim_date[date]` axis, Total Revenue + Total Profit.
3. **Mix:** Donut by `dim_region[region]`; bar by `dim_product[category]`.
4. **Table:** Top products (`product_name`, Total Revenue, Total Profit,
   Profit Margin, Total Orders) with conditional formatting on margin < 10%.
5. **Slicers:** `dim_date[date]` (relative or range), region, category,
   `dim_channel[channel]`, `fact_sales[order_status]`. Default the status
   slicer to exclude `Cancelled` to match the app.
