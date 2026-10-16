"""analytics views (mirrors database/views/*.sql, embedded for Docker-safe migrate)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

VIEWS = [
    """
    DROP VIEW IF EXISTS v_daily_sales;
    CREATE VIEW v_daily_sales AS
    SELECT d.date_key, d.date AS sale_date, d.year, d.quarter, d.month,
           d.month_name, d.weekday, d.weekday_name, d.is_weekend,
           COUNT(DISTINCT f.order_id) AS orders, SUM(f.quantity) AS units,
           SUM(f.revenue) AS revenue, SUM(f.cost * f.quantity) AS cost_goods,
           SUM(f.shipping_cost) AS shipping, SUM(f.profit) AS profit,
           CASE WHEN COUNT(DISTINCT f.order_id) = 0 THEN 0
                ELSE SUM(f.revenue) / COUNT(DISTINCT f.order_id) END AS avg_order_value,
           CASE WHEN SUM(f.revenue) = 0 THEN 0
                ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin
    FROM dim_date d LEFT JOIN fact_sales f
      ON f.date_key = d.date_key AND f.is_deleted = FALSE
    GROUP BY d.date_key, d.date, d.year, d.quarter, d.month, d.month_name,
             d.weekday, d.weekday_name, d.is_weekend
    """,
    """
    DROP VIEW IF EXISTS v_monthly_sales;
    CREATE VIEW v_monthly_sales AS
    SELECT d.year, d.month, MIN(d.date) AS month_start,
           COUNT(DISTINCT f.order_id) AS orders, SUM(f.quantity) AS units,
           SUM(f.revenue) AS revenue, SUM(f.profit) AS profit,
           CASE WHEN SUM(f.revenue) = 0 THEN 0
                ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin,
           CASE WHEN COUNT(DISTINCT f.order_id) = 0 THEN 0
                ELSE SUM(f.revenue) / COUNT(DISTINCT f.order_id) END AS avg_order_value
    FROM dim_date d LEFT JOIN fact_sales f
      ON f.date_key = d.date_key AND f.is_deleted = FALSE
    GROUP BY d.year, d.month
    """,
    """
    DROP VIEW IF EXISTS v_sales_by_region;
    CREATE VIEW v_sales_by_region AS
    SELECT r.region, r.country, COUNT(DISTINCT f.order_id) AS orders,
           SUM(f.quantity) AS units, SUM(f.revenue) AS revenue, SUM(f.profit) AS profit,
           CASE WHEN SUM(f.revenue) = 0 THEN 0
                ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin
    FROM fact_sales f LEFT JOIN dim_region r ON r.id = f.region_key
    WHERE f.is_deleted = FALSE GROUP BY r.region, r.country
    """,
    """
    DROP VIEW IF EXISTS v_sales_by_product;
    CREATE VIEW v_sales_by_product AS
    SELECT p.product_id, p.product_name, p.category, p.subcategory,
           COUNT(DISTINCT f.order_id) AS orders, SUM(f.quantity) AS units,
           SUM(f.revenue) AS revenue, SUM(f.profit) AS profit,
           CASE WHEN SUM(f.revenue) = 0 THEN 0
                ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin,
           CASE WHEN SUM(f.quantity) = 0 THEN 0
                ELSE SUM(f.revenue) / SUM(f.quantity) END AS revenue_per_unit
    FROM fact_sales f LEFT JOIN dim_product p ON p.id = f.product_key
    WHERE f.is_deleted = FALSE
    GROUP BY p.product_id, p.product_name, p.category, p.subcategory
    """,
    """
    DROP VIEW IF EXISTS v_sales_by_category;
    CREATE VIEW v_sales_by_category AS
    SELECT p.category, COUNT(DISTINCT f.order_id) AS orders,
           SUM(f.quantity) AS units, SUM(f.revenue) AS revenue, SUM(f.profit) AS profit,
           CASE WHEN SUM(f.revenue) = 0 THEN 0
                ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin,
           AVG(f.discount) AS avg_discount
    FROM fact_sales f LEFT JOIN dim_product p ON p.id = f.product_key
    WHERE f.is_deleted = FALSE GROUP BY p.category
    """,
    """
    DROP VIEW IF EXISTS v_sales_by_channel;
    CREATE VIEW v_sales_by_channel AS
    SELECT c.channel, COUNT(DISTINCT f.order_id) AS orders,
           SUM(f.quantity) AS units, SUM(f.revenue) AS revenue, SUM(f.profit) AS profit,
           CASE WHEN SUM(f.revenue) = 0 THEN 0
                ELSE SUM(f.profit) / SUM(f.revenue) END AS profit_margin
    FROM fact_sales f LEFT JOIN dim_channel c ON c.id = f.channel_key
    WHERE f.is_deleted = FALSE GROUP BY c.channel
    """,
    """
    DROP VIEW IF EXISTS v_customer_ltv;
    CREATE VIEW v_customer_ltv AS
    SELECT cu.customer_id, cu.customer_name, cu.segment,
           COUNT(DISTINCT f.order_id) AS orders, SUM(f.quantity) AS units,
           SUM(f.revenue) AS revenue, SUM(f.profit) AS profit,
           CASE WHEN COUNT(DISTINCT f.order_id) = 0 THEN 0
                ELSE SUM(f.revenue) / COUNT(DISTINCT f.order_id) END AS avg_order_value,
           MIN(d.date) AS first_order, MAX(d.date) AS last_order
    FROM fact_sales f JOIN dim_customer cu ON cu.id = f.customer_key
    LEFT JOIN dim_date d ON d.date_key = f.date_key
    WHERE f.is_deleted = FALSE
    GROUP BY cu.customer_id, cu.customer_name, cu.segment
    """,
]


def upgrade() -> None:
    for stmt in VIEWS:
        # split DROP + CREATE (sqlite/postgres compatible, no multi-exec)
        for part in [s.strip() for s in stmt.strip().split(";") if s.strip()]:
            op.execute(part)


def downgrade() -> None:
    for name in [
        "v_customer_ltv",
        "v_sales_by_channel",
        "v_sales_by_category",
        "v_sales_by_product",
        "v_sales_by_region",
        "v_monthly_sales",
        "v_daily_sales",
    ]:
        op.execute(f"DROP VIEW IF EXISTS {name}")
