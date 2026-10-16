"""Power BI export bundle: cleaned fact + dimension CSVs in one ZIP."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.analytics.filters import filtered, resolve_period
from app.analytics.kpi_catalog import KPI_DEFINITIONS
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
Grain: one row per order line. Cancelled orders excluded unless the export
was run with an explicit status filter (see manifest.json).
See docs/powerbi.md for the star-schema diagram, import guidance and DAX measures.
"""

DATA_DICTIONARY = """table,column,description
fact_sales,order_id,Business order identifier (distinct count = Total Orders)
fact_sales,date_key,YYYYMMDD key to dim_date
fact_sales,customer_key,FK to dim_customer.id
fact_sales,product_key,FK to dim_product.id
fact_sales,region_key,FK to dim_region.id
fact_sales,channel_key,FK to dim_channel.id
fact_sales,rep_key,FK to dim_sales_rep.id
fact_sales,quantity,Units sold
fact_sales,unit_price,Unit price (Numeric 12,2)
fact_sales,discount,Discount fraction 0-1
fact_sales,cost,Unit cost (Numeric 12,2)
fact_sales,shipping_cost,Shipping per line
fact_sales,revenue,Net sales = qty*price*(1-discount)
fact_sales,profit,profit = revenue - cost*qty - shipping
fact_sales,order_status,Completed/Cancelled/etc.
fact_sales,batch_id,Import batch for lineage
dim_date,date_key,YYYYMMDD primary key
dim_customer,customer_id,Stable natural key (repeat logic uses this)
dim_product,product_id,Stable natural key
dim_region,region,Region + country unique
dim_channel,channel,Sales channel
dim_sales_rep,rep_name,Sales representative
"""

RELATIONSHIPS = """# Relationships (Many-to-One, single direction)
fact_sales[customer_key] -> dim_customer[id]
fact_sales[product_key] -> dim_product[id]
fact_sales[region_key] -> dim_region[id]
fact_sales[channel_key] -> dim_channel[id]
fact_sales[rep_key] -> dim_sales_rep[id]
fact_sales[date_key] -> dim_date[date_key]
Cardinality: Many to One. Use dim_date[date] as the date table (mark as date table).
Row-count check: fact rows in ZIP must equal manifest.json fact_rows.
"""


def _dax_text() -> str:
    p = Path(__file__).resolve().parents[3] / "database" / "dax" / "measures.dax"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return "// DAX measures missing from bundle (see docs/powerbi.md)\n"


def build_bundle(db: Session, f: dict | None = None) -> bytes:
    cf, ct, _, _ = resolve_period(f or {})
    fq = (
        filtered(db, f or {}, cf, ct)
        if f
        else db.query(FactSale).filter(
            FactSale.is_deleted.is_(False),
            (FactSale.order_status.is_(None)) | (FactSale.order_status != "Cancelled"),
        )
    )
    facts = fq.all()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # fact
        cols = TABLES[0][2]
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(cols)
        for row in facts:
            w.writerow([getattr(row, c) for c in cols])
        z.writestr("fact_sales.csv", out.getvalue())
        # dims restricted to referenced keys (keeps bundle consistent + small)
        used = {
            "customer": {x.customer_key for x in facts if x.customer_key},
            "product": {x.product_key for x in facts if x.product_key},
            "region": {x.region_key for x in facts if x.region_key},
            "channel": {x.channel_key for x in facts if x.channel_key},
            "rep": {x.rep_key for x in facts if x.rep_key},
            "date": {x.date_key for x in facts},
        }
        dim_queries = {
            "dim_customer.csv": (
                DimCustomer,
                ["id", "customer_id", "customer_name", "segment"],
                "customer",
            ),
            "dim_product.csv": (
                DimProduct,
                ["id", "product_id", "product_name", "category", "subcategory"],
                "product",
            ),
            "dim_region.csv": (DimRegion, ["id", "region", "country"], "region"),
            "dim_channel.csv": (DimChannel, ["id", "channel"], "channel"),
            "dim_sales_rep.csv": (DimRep, ["id", "rep_name"], "rep"),
        }
        for name, (model, dcols, key) in dim_queries.items():
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(dcols)
            ids = used[key]
            rows = db.query(model).filter(model.id.in_(ids)).all() if ids else []  # type: ignore[attr-defined]
            for row in rows:
                w.writerow([getattr(row, c) for c in dcols])
            z.writestr(name, out.getvalue())
        # dim_date
        out = io.StringIO()
        w = csv.writer(out)
        dcols = [
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
        ]
        w.writerow(dcols)
        for row in (
            db.query(DimDate).filter(DimDate.date_key.in_(used["date"])).all()
            if used["date"]
            else []
        ):
            w.writerow([getattr(row, c) for c in dcols])
        z.writestr("dim_date.csv", out.getvalue())
        # docs
        z.writestr("README.txt", README)
        z.writestr("data_dictionary.csv", DATA_DICTIONARY)
        z.writestr("relationships.md", RELATIONSHIPS)
        z.writestr("measures.dax", _dax_text())
        z.writestr("kpi_definitions.json", json.dumps(KPI_DEFINITIONS, indent=2))
        manifest = {
            "exported_at": datetime.now(UTC).isoformat(),
            "grain": "one row per order line",
            "filters": f or {},
            "fact_rows": len(facts),
            "revenue_total": round(sum(float(x.revenue or 0) for x in facts), 2),
            "profit_total": round(sum(float(x.profit or 0) for x in facts), 2),
            "orders": len({x.order_id for x in facts}),
        }
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
    buf.seek(0)
    return buf.getvalue()
