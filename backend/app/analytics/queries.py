"""Aggregate breakdowns: timeseries, dims, discount buckets, order table."""

from __future__ import annotations

from datetime import date

from sqlalchemy import case, func

from app.analytics.filters import filtered, growth
from app.models.entities import (
    DimChannel,
    DimCustomer,
    DimDate,
    DimProduct,
    DimRegion,
    FactSale,
)


def _pack(row, labels: list[str]) -> dict:
    d = {label: row[i] for i, label in enumerate(labels)}
    d["revenue"] = float(row[len(labels)])
    d["profit"] = float(row[len(labels) + 1])
    d["orders"] = int(row[len(labels) + 2])
    d["units"] = float(row[len(labels) + 3])
    d["margin"] = (d["profit"] / d["revenue"]) if d["revenue"] else 0.0
    return d


def _grouped(db, f, d_from, d_to, cols, labels, join_date=False):
    from app.analytics.filters import AGG

    q = filtered(db, f, d_from, d_to)
    if join_date:
        q = q.outerjoin(DimDate, DimDate.date_key == FactSale.date_key)
    q = q.with_entities(*cols, *AGG).group_by(*cols)
    return [_pack(r, labels) for r in q.all()]


def _with_prev(cur: list[dict], prev: list[dict], key: str) -> list[dict]:
    pmap = {r[key]: r for r in prev}
    for r in cur:
        p = pmap.get(r[key])
        r["revenue_growth"] = growth(r["revenue"], p["revenue"] if p else None)
        r["profit_growth"] = growth(r["profit"], p["profit"] if p else None)
    return sorted(cur, key=lambda r: r["revenue"], reverse=True)


def timeseries(db, f, cf: date | None, ct: date | None) -> dict:
    span = (ct - cf).days if cf and ct else 999
    cols: list
    labels: list[str]
    if span <= 62:
        cols, labels = [DimDate.date], ["date"]
    else:
        cols = [DimDate.year, DimDate.month]
        labels = ["year", "month"]
    cur = _grouped(db, f, cf, ct, cols, labels, join_date=True)
    for r in cur:
        if "date" in r and r["date"] is not None:
            r["date"] = str(r["date"])
        r["aov"] = (r["revenue"] / r["orders"]) if r["orders"] else 0.0
    grain = "daily" if span <= 62 else "monthly"
    return {"grain": grain, "points": cur}


def by_region(db, f, cf, ct, pf, pt):
    cur = _grouped(db, f, cf, ct, [DimRegion.region, DimRegion.country], ["region", "country"])
    prev = _grouped(db, f, pf, pt, [DimRegion.region], ["region"]) if pf else []
    pmap = {r["region"]: r for r in prev}
    for r in cur:
        p = pmap.get(r["region"])
        r["revenue_growth"] = growth(r["revenue"], p["revenue"] if p else None)
    return sorted(cur, key=lambda r: r["revenue"], reverse=True)


def by_channel(db, f, cf, ct, pf, pt):
    cur = _grouped(db, f, cf, ct, [DimChannel.channel], ["channel"])
    prev = _grouped(db, f, pf, pt, [DimChannel.channel], ["channel"]) if pf else []
    return _with_prev(cur, prev, "channel")


def by_category(db, f, cf, ct, pf, pt):
    cur = _grouped(db, f, cf, ct, [DimProduct.category], ["category"])
    prev = _grouped(db, f, pf, pt, [DimProduct.category], ["category"]) if pf else []
    out = _with_prev(cur, prev, "category")
    # avg discount per category (current period)
    disc = (
        filtered(db, f, cf, ct)
        .with_entities(DimProduct.category, func.avg(FactSale.discount))
        .group_by(DimProduct.category)
        .all()
    )
    dmap = {r[0]: float(r[1] or 0) for r in disc}
    for r in out:
        r["avg_discount"] = dmap.get(r["category"], 0.0)
    return out


def by_product(db, f, cf, ct, limit: int = 50):
    rows = _grouped(
        db,
        f,
        cf,
        ct,
        [
            DimProduct.product_id,
            DimProduct.product_name,
            DimProduct.category,
            DimProduct.subcategory,
        ],
        ["product_id", "product_name", "category", "subcategory"],
    )
    rows = sorted(rows, key=lambda r: r["revenue"], reverse=True)[:limit]
    for r in rows:
        r["low_margin"] = r["margin"] < 0.10 and r["revenue"] > 0
    return rows


def top_customers(db, f, cf, ct, limit: int = 20):
    rows = _grouped(
        db,
        f,
        cf,
        ct,
        [DimCustomer.customer_id, DimCustomer.customer_name, DimCustomer.segment],
        ["customer_id", "customer_name", "segment"],
    )
    rows = [r for r in rows if r["customer_id"]]
    rows = sorted(rows, key=lambda r: r["revenue"], reverse=True)[:limit]
    for r in rows:
        r["aov"] = (r["revenue"] / r["orders"]) if r["orders"] else 0.0
    return rows


def segment_mix(db, f, cf, ct):
    return sorted(
        _grouped(db, f, cf, ct, [DimCustomer.segment], ["segment"]),
        key=lambda r: r["revenue"],
        reverse=True,
    )


def discount_buckets(db, f, cf, ct):
    bucket = case(
        (FactSale.discount <= 0.001, "none"), (FactSale.discount <= 0.10, "low"), else_="high"
    ).label("bucket")
    from app.analytics.filters import AGG

    rows = filtered(db, f, cf, ct).with_entities(bucket, *AGG).group_by(bucket).all()
    out = [
        {
            "bucket": r[0],
            "revenue": float(r[1]),
            "profit": float(r[2]),
            "orders": int(r[3]),
            "units": float(r[4]),
        }
        for r in rows
    ]
    for r in out:
        r["margin"] = (r["profit"] / r["revenue"]) if r["revenue"] else 0.0
    order = {"none": 0, "low": 1, "high": 2}
    return sorted(out, key=lambda r: order.get(r["bucket"], 9))


SORTABLE = {
    "order_date": FactSale.date_key,
    "revenue": FactSale.revenue,
    "profit": FactSale.profit,
    "quantity": FactSale.quantity,
    "order_id": FactSale.order_id,
}


def orders_table(
    db,
    f,
    cf,
    ct,
    page: int = 1,
    page_size: int = 25,
    sort: str = "order_date",
    direction: str = "desc",
    search: str | None = None,
):
    sort_col = SORTABLE.get(sort, FactSale.date_key)
    order = sort_col.desc() if direction == "desc" else sort_col.asc()
    q = filtered(db, f, cf, ct).outerjoin(DimDate, DimDate.date_key == FactSale.date_key)
    if search:
        like = f"%{search}%"
        q = q.filter(FactSale.order_id.ilike(like) | DimProduct.product_name.ilike(like))
    total = q.with_entities(func.count(func.distinct(FactSale.id))).scalar() or 0
    rows = (
        q.with_entities(
            FactSale.order_id,
            DimDate.date,
            DimCustomer.customer_name,
            DimProduct.product_name,
            DimProduct.category,
            DimRegion.region,
            DimChannel.channel,
            FactSale.quantity,
            FactSale.revenue,
            FactSale.profit,
            FactSale.order_status,
        )
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "order_id": r[0],
            "order_date": str(r[1]) if r[1] else None,
            "customer": r[2],
            "product": r[3],
            "category": r[4],
            "region": r[5],
            "channel": r[6],
            "quantity": float(r[7]),
            "revenue": float(r[8]),
            "profit": float(r[9]),
            "status": r[10],
        }
        for r in rows
    ]
    return {"total": total, "page": page, "page_size": page_size, "items": items}
