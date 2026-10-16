# Upload schema

Canonical fields (map file columns onto these in the wizard):

`order_id`, `order_date`, `customer_id`, `customer_name`,
`customer_segment`, `product_id`, `product_name`, `category`,
`subcategory`, `region`, `country`, `sales_channel`, `sales_rep`,
`quantity`, `unit_price`, `discount`, `cost`, `shipping_cost`,
`revenue`, `profit`, `payment_method`, `order_status`

Required: `order_id`, `order_date`, `quantity`, one of
(`product_id`|`product_name`), one of (`revenue`|`unit_price`).

Recognized aliases (non-exhaustive — full map in
`backend/app/ingestion/aliases.py`):

| Canonical | Aliases |
|---|---|
| `order_date` | `date`, `transaction_date`, `invoice_date`, `sale_date` |
| `revenue` | `sales`, `amount`, `total_amount`, `total`, `net` |
| `quantity` | `qty`, `units` |
| `customer_name` | `client`, `customer`, `buyer`, `company` |
| `region` | `state`, `territory`, `market`, `area` |
| `discount` | `disc`, `discount_pct`, `promo` (0–100 scale auto-converted) |
| `sales_channel` | `channel`, `platform` |
| `sales_rep` | `rep`, `salesperson`, `agent` |
| `shipping_cost` | `shipping`, `freight`, `delivery_cost` |

Unmapped columns are ignored. Original file bytes, hash, mapping JSON and
per-row payloads are retained (`uploaded_files`, `import_jobs`,
`raw_sales_records`) for audit and re-runs.
