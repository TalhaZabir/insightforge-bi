-- Revenue and profit by product + margin flags
DROP VIEW IF EXISTS v_sales_by_product;
CREATE VIEW v_sales_by_product AS
SELECT
  p.product_id,
  p.product_name,
  p.category,
  p.subcategory,
  COUNT(DISTINCT f.order_id) AS orders,
  SUM(f.quantity) AS units,
  SUM(f.revenue) AS revenue,
  SUM(f.profit) AS profit,
  CASE WHEN SUM(f.revenue) = 0 THEN 0
       ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin,
  CASE WHEN SUM(f.quantity) = 0 THEN 0
       ELSE SUM(f.revenue) / SUM(f.quantity) END AS revenue_per_unit
FROM fact_sales f
LEFT JOIN dim_product p ON p.id = f.product_key
WHERE f.is_deleted = FALSE
GROUP BY p.product_id, p.product_name, p.category, p.subcategory;
