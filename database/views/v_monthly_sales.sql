-- Monthly sales performance
DROP VIEW IF EXISTS v_monthly_sales;
CREATE VIEW v_monthly_sales AS
SELECT
  d.year,
  d.month,
  MIN(d.date) AS month_start,
  COUNT(DISTINCT f.order_id) AS orders,
  SUM(f.quantity) AS units,
  SUM(f.revenue) AS revenue,
  SUM(f.profit) AS profit,
  CASE WHEN SUM(f.revenue) = 0 THEN 0
       ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin,
  CASE WHEN COUNT(DISTINCT f.order_id) = 0 THEN 0
       ELSE SUM(f.revenue) / COUNT(DISTINCT f.order_id) END AS avg_order_value
FROM dim_date d
LEFT JOIN fact_sales f ON f.date_key = d.date_key AND f.is_deleted = FALSE
GROUP BY d.year, d.month;
