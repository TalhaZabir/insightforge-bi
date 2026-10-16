"""fact money Float -> Numeric(12,2) for exact financial arithmetic.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

MONEY_COLS = ["quantity", "unit_price", "cost", "shipping_cost", "revenue", "profit"]


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def _drop_views() -> None:
    for v in [
        "v_customer_ltv",
        "v_sales_by_channel",
        "v_sales_by_category",
        "v_sales_by_product",
        "v_sales_by_region",
        "v_monthly_sales",
        "v_daily_sales",
    ]:
        op.execute(f"DROP VIEW IF EXISTS {v}")


def _recreate_views() -> None:
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).parent / "0002_analytics_views.py"
    spec = importlib.util.spec_from_file_location("v0002_views", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for stmt in mod.VIEWS:
        for part in [s.strip() for s in stmt.strip().split(";") if s.strip()]:
            # stmt already contains DROP + CREATE; run CREATE part only
            if part.upper().startswith("CREATE"):
                op.execute(part)


def upgrade() -> None:
    # Views depend on fact_sales money columns on Postgres (ALTER TYPE is
    # blocked while dependents exist), and SQLite batch mode recreates the
    # table (views break the rename). Drop first on both, recreate after.
    _drop_views()
    if _is_sqlite():
        # SQLite: batch_alter recreates table; backfill rounds to 2dp.
        with op.batch_alter_table("fact_sales") as batch:
            for col in MONEY_COLS:
                batch.alter_column(col, existing_type=sa.Float(), type_=sa.Numeric(12, 2))
            batch.alter_column("discount", existing_type=sa.Float(), type_=sa.Numeric(12, 4))
    else:
        for col in MONEY_COLS:
            op.execute(f"UPDATE fact_sales SET {col} = ROUND({col}::numeric, 2)")
        op.execute("UPDATE fact_sales SET discount = ROUND(discount::numeric, 4)")
        for col in MONEY_COLS:
            op.alter_column(
                "fact_sales",
                col,
                existing_type=sa.Float(),
                type_=sa.Numeric(12, 2),
                postgresql_using=f"{col}::numeric(12,2)",
            )
        op.alter_column(
            "fact_sales",
            "discount",
            existing_type=sa.Float(),
            type_=sa.Numeric(12, 4),
            postgresql_using="discount::numeric(12,4)",
        )
    _recreate_views()


def downgrade() -> None:
    if _is_sqlite():
        with op.batch_alter_table("fact_sales") as batch:
            for col in MONEY_COLS + ["discount"]:
                batch.alter_column(col, existing_type=sa.Numeric(), type_=sa.Float())
    else:
        for col in MONEY_COLS + ["discount"]:
            op.alter_column("fact_sales", col, existing_type=sa.Numeric(), type_=sa.Float())
