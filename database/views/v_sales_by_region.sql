-- Revenue and profit by region (with ranking inputs)
DROP VIEW IF EXISTS v_sales_by_region;
CREATE VIEW v_sales_by_region AS
SELECT
  r.region,
  r.country,
  COUNT(DISTINCT f.order_id) AS orders,
  SUM(f.quantity) AS units,
  SUM(f.revenue) AS revenue,
  SUM(f.profit) AS profit,
  CASE WHEN SUM(f.revenue) = 0 THEN 0
       ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin
FROM fact_sales f
LEFT JOIN dim_region r ON r.id = f.region_key
WHERE f.is_deleted = FALSE
GROUP BY r.region, r.country;
