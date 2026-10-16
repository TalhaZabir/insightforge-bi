-- Customer lifetime value + top-customer inputs
DROP VIEW IF EXISTS v_customer_ltv;
CREATE VIEW v_customer_ltv AS
SELECT
  cu.customer_id,
  cu.customer_name,
  cu.segment,
  COUNT(DISTINCT f.order_id) AS orders,
  SUM(f.quantity) AS units,
  SUM(f.revenue) AS revenue,
  SUM(f.profit) AS profit,
  CASE WHEN COUNT(DISTINCT f.order_id) = 0 THEN 0
       ELSE SUM(f.revenue) / COUNT(DISTINCT f.order_id) END AS avg_order_value,
  MIN(d.date) AS first_order,
  MAX(d.date) AS last_order
FROM fact_sales f
JOIN dim_customer cu ON cu.id = f.customer_key
LEFT JOIN dim_date d ON d.date_key = f.date_key
WHERE f.is_deleted = FALSE
GROUP BY cu.customer_id, cu.customer_name, cu.segment;
