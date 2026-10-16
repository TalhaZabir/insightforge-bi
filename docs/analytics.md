# Analytics definitions

All endpoints share `?from&to&region&country&category&subcategory&product&segment&channel&rep&status`.

- **Cancelled rule:** `order_status = 'Cancelled'` rows are excluded unless
  `?status=` is passed explicitly. `NULL`/other statuses are included.
- **Growth:** previous *equivalent* period = same day-count immediately
  before `from`. `growth = (cur − prev) / |prev| × 100`; `None` when no
  previous period or `prev = 0`. Margin move is reported in **pp**.
- **KPIs:** revenue `SUM(revenue)`; profit `SUM(profit)`; margin
  `profit/revenue`; orders `COUNT(DISTINCT order_id)`; units `SUM(quantity)`;
  AOV `revenue/orders`.
- **Customers:** active = ≥1 in-period row; **new** = first-ever order inside
  the period; **returning** = first-ever order before `from`;
  repeat rate = returning / active. Cancelled rows confer no activity.
- **Discount buckets:** none (0), low (≤10%), high (>10%) on the stored
  0–1 fraction. The DAX `Discount Rate` is the row average to match.
- **Timeseries grain:** daily when the span ≤ 62 days, else monthly.
- **Insights:** 10 deterministic rules over these exact numbers
  (trend, margin, best/worst region, low-margin heroes, category growth,
  repeat-rate move, discount drag, top-3 concentration, data quality).
  Share guards (8% region / 10% category) suppress small-base noise.
