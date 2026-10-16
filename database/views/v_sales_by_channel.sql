-- Revenue by sales channel
DROP VIEW IF EXISTS v_sales_by_channel;
CREATE VIEW v_sales_by_channel AS
SELECT
  c.channel,
  COUNT(DISTINCT f.order_id) AS orders,
  SUM(f.quantity) AS units,
  SUM(f.revenue) AS revenue,
  SUM(f.profit) AS profit,
  CASE WHEN SUM(f.revenue) = 0 THEN 0
       ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin
FROM fact_sales f
LEFT JOIN dim_channel c ON c.id = f.channel_key
WHERE f.is_deleted = FALSE
GROUP BY c.channel;
