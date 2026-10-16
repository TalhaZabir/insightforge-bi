# Analytics definitions

All endpoints share `?from&to&region&country&category&subcategory&product&segment&channel&rep&status`.

- **Cancelled rule:** `order_status = 'Cancelled'` rows are excluded unless
  `?status=` is passed explicitly. `NULL`/other statuses are included.
- **Growth:** previous *equivalent* period = same day-count immediately
  before `from`. `growth = (cur − prev) / |prev| × 100`; `None` (UI: "N/A" /
  "Insufficient history") when no previous period or `prev = 0`. Negative
  baselines use `|prev|`. Margin move is reported in **pp**.
- **KPIs (single source of truth: `backend/app/analytics/kpi_catalog.py`):**
  revenue `SUM(revenue)` net of discounts; profit `SUM(profit)` =
  revenue − cost×qty − shipping; margin `profit/revenue` (weighted, never
  averaged; `None` when revenue is 0); orders `COUNT(DISTINCT order_id)`;
  units `SUM(quantity)`; AOV `revenue/orders` (`None` when orders is 0).
  Money stored as `Numeric(12,2)` (migration `0003`); discount as
  `Numeric(12,4)` fraction. Low-margin flag: margin < 10% with revenue > 0.
- **Customers:** active = ≥1 in-period row; **new** = first-ever order inside
  the period; **returning** = first-ever order before `from`;
  repeat rate = returning / active (lifetime definition, labelled in UI).
  Cancelled rows confer no activity.
- **RFM:** quintile R/F/M scores 1..5 within current filters (Recency = days
  from period-end to last purchase, lower is better). Labels: Champions
  (13–15), Loyal (10–12), Potential (7–9), At-risk (5–6), Hibernating (3–4).
- **Cohorts:** acquisition month = first-ever qualifying purchase; retention =
  active members / cohort size; `null` = incomplete month, `0` = no activity.
- **Declining:** second-half revenue < 70% of first-half (dated ranges only).
- **Discount buckets:** none (0), low (≤10%), high (>10%) on the stored
  0–1 fraction. The DAX `Discount Rate` is the row average to match.
- **Timeseries grain:** daily when the span ≤ 62 days, else monthly.
- **Forecasting (`GET /analytics/forecast?horizon=3`):** monthly revenue,
  gap-filled with 0; requires ≥12 months else "Insufficient history".
  Chronological 80/20 split; candidates naive / seasonal-naive / MA(3);
  winner by lowest WAPE; refit on full history. Reports MAE/RMSE/WAPE
  (no MAPE — actuals may be zero).
- **Targets:** `monthly_targets` (month, revenue_target, profit_target).
  `GET /analytics/targets/tracking?month=YYYY-MM` returns actual vs target,
  absolute + % variance (via `growth`), progress % and required daily revenue.
- **Insights:** 12 deterministic rules over these exact numbers
  (trend, margin, best/worst region, low-margin heroes, category growth,
  repeat-rate move, discount drag, top-3 concentration, data quality,
  **target variance, forecast risk**). Thresholds configurable via
  `INS_*` env vars (see `thresholds()` in `engine.py`). Share guards (8%
  region / 10% category) suppress small-base noise. Headlines deduped;
  frontend supports dismiss (localStorage).
