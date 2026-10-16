"""Power BI export bundle: cleaned fact + dimension CSVs in one ZIP."""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import (
    DimChannel,
    DimCustomer,
    DimDate,
    DimProduct,
    DimRegion,
    DimRep,
    FactSale,
)

TABLES: list[tuple[str, Any, list[str]]] = [
    (
        "fact_sales.csv",
        FactSale,
        [
            "order_id",
            "date_key",
            "customer_key",
            "product_key",
            "region_key",
            "channel_key",
            "rep_key",
            "quantity",
            "unit_price",
            "discount",
            "cost",
            "shipping_cost",
            "revenue",
            "profit",
            "payment_method",
            "order_status",
            "batch_id",
        ],
    ),
    (
        "dim_date.csv",
        DimDate,
        [
            "date_key",
            "date",
            "year",
            "quarter",
            "month",
            "month_name",
            "day",
            "weekday",
            "weekday_name",
            "is_weekend",
        ],
    ),
    ("dim_customer.csv", DimCustomer, ["id", "customer_id", "customer_name", "segment"]),
    (
        "dim_product.csv",
        DimProduct,
        ["id", "product_id", "product_name", "category", "subcategory"],
    ),
    ("dim_region.csv", DimRegion, ["id", "region", "country"]),
    ("dim_channel.csv", DimChannel, ["id", "channel"]),
    ("dim_sales_rep.csv", DimRep, ["id", "rep_name"]),
]

README = """InsightForge BI — Power BI export
================================
fact_sales joins dimensions on *_key columns (= dimension id, except
date_key which is YYYYMMDD matching dim_date.date_key).
See docs/powerbi.md for the star-schema diagram, import guidance and DAX measures.
Default reporting excludes Cancelled orders (see analytics API `status` filter).
"""


def build_bundle(db: Session) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, model, cols in TABLES:
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(cols)
            for row in db.query(model).yield_per(2000):
                w.writerow([getattr(row, c) for c in cols])
            z.writestr(name, out.getvalue())
        z.writestr("README.txt", README)
    buf.seek(0)
    return buf.getvalue()
