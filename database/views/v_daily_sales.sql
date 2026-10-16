-- Daily sales performance (Power BI + dashboards)
-- Grain: one row per calendar date present in dim_date with sales.
DROP VIEW IF EXISTS v_daily_sales;
CREATE VIEW v_daily_sales AS
SELECT
  d.date_key,
  d.date AS sale_date,
  d.year,
  d.quarter,
  d.month,
  d.month_name,
  d.weekday,
  d.weekday_name,
  d.is_weekend,
  COUNT(DISTINCT f.order_id) AS orders,
  SUM(f.quantity) AS units,
  SUM(f.revenue) AS revenue,
  SUM(f.cost * f.quantity) AS cost_goods,
  SUM(f.shipping_cost) AS shipping,
  SUM(f.profit) AS profit,
  CASE WHEN COUNT(DISTINCT f.order_id) = 0 THEN 0
       ELSE SUM(f.revenue) / COUNT(DISTINCT f.order_id) END AS avg_order_value,
  CASE WHEN SUM(f.revenue) = 0 THEN 0
       ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin
FROM dim_date d
LEFT JOIN fact_sales f ON f.date_key = d.date_key AND f.is_deleted = FALSE
GROUP BY d.date_key, d.date, d.year, d.quarter, d.month, d.month_name,
         d.weekday, d.weekday_name, d.is_weekend;
