-- Revenue and profit by category
DROP VIEW IF EXISTS v_sales_by_category;
CREATE VIEW v_sales_by_category AS
SELECT
  p.category,
  COUNT(DISTINCT f.order_id) AS orders,
  SUM(f.quantity) AS units,
  SUM(f.revenue) AS revenue,
  SUM(f.profit) AS profit,
  CASE WHEN SUM(f.revenue) = 0 THEN 0
       ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin,
  AVG(f.discount) AS avg_discount
FROM fact_sales f
LEFT JOIN dim_product p ON p.id = f.product_key
WHERE f.is_deleted = FALSE
GROUP BY p.category;
