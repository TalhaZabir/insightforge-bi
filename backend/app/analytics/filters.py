"""Shared filter parsing + filtered fact query builder (no N+1: all SQL aggregates)."""

from __future__ import annotations

from datetime import date

from fastapi import Query
from sqlalchemy import false, func
from sqlalchemy.orm import Session

from app.analytics.kpi_catalog import (
    growth as catalog_growth,
)
from app.analytics.kpi_catalog import (
    pack_kpi_row,
    to_float,
)
from app.analytics.kpi_catalog import (
    repeat_rate as catalog_repeat_rate,
)
from app.models.entities import (
    DimChannel,
    DimCustomer,
    DimDate,
    DimProduct,
    DimRegion,
    DimRep,
    FactSale,
)


def common_filters(
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    region: list[str] | None = Query(default=None),
    country: list[str] | None = Query(default=None),
    category: list[str] | None = Query(default=None),
    subcategory: list[str] | None = Query(default=None),
    product: list[str] | None = Query(default=None),
    segment: list[str] | None = Query(default=None),
    channel: list[str] | None = Query(default=None),
    rep: list[str] | None = Query(default=None),
    status: list[str] | None = Query(default=None),
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "region": region,
        "country": country,
        "category": category,
        "subcategory": subcategory,
        "product": product,
        "segment": segment,
        "channel": channel,
        "rep": rep,
        "status": status,
    }


def _parse(d: str | None) -> date | None:
    return date.fromisoformat(d) if d else None


def resolve_period(f: dict) -> tuple[date | None, date | None, date | None, date | None]:
    """Returns (cur_from, cur_to, prev_from, prev_to). Previous = same length before cur_from."""
    cf, ct = _parse(f.get("date_from")), _parse(f.get("date_to"))
    if cf and ct and ct >= cf:
        length = (ct - cf).days + 1
        pf = date.fromordinal(cf.toordinal() - length)
        pt = date.fromordinal(cf.toordinal() - 1)
        return cf, ct, pf, pt
    return cf, ct, None, None


def _date_keys(db: Session, d_from: date | None, d_to: date | None) -> list[int] | None:
    if d_from is None and d_to is None:
        return None
    q = db.query(DimDate.date_key)
    if d_from:
        q = q.filter(DimDate.date >= d_from)
    if d_to:
        q = q.filter(DimDate.date <= d_to)
    return [r[0] for r in q.all()]


def filtered(db: Session, f: dict, d_from: date | None, d_to: date | None):
    """Base fact query with all dimension filters applied."""
    keys = _date_keys(db, d_from, d_to)
    q = (
        db.query(FactSale)
        .outerjoin(DimCustomer, DimCustomer.id == FactSale.customer_key)
        .outerjoin(DimProduct, DimProduct.id == FactSale.product_key)
        .outerjoin(DimRegion, DimRegion.id == FactSale.region_key)
        .outerjoin(DimChannel, DimChannel.id == FactSale.channel_key)
        .outerjoin(DimRep, DimRep.id == FactSale.rep_key)
        .filter(FactSale.is_deleted.is_(False))
    )
    if keys is not None:
        q = q.filter(FactSale.date_key.in_(keys)) if keys else q.filter(false())
    if f.get("region"):
        q = q.filter(DimRegion.region.in_(f["region"]))
    if f.get("country"):
        q = q.filter(DimRegion.country.in_(f["country"]))
    if f.get("category"):
        q = q.filter(DimProduct.category.in_(f["category"]))
    if f.get("subcategory"):
        q = q.filter(DimProduct.subcategory.in_(f["subcategory"]))
    if f.get("product"):
        q = q.filter(DimProduct.product_id.in_(f["product"]))
    if f.get("segment"):
        q = q.filter(DimCustomer.segment.in_(f["segment"]))
    if f.get("channel"):
        q = q.filter(DimChannel.channel.in_(f["channel"]))
    if f.get("rep"):
        q = q.filter(DimRep.rep_name.in_(f["rep"]))
    if f.get("status"):
        q = q.filter(FactSale.order_status.in_(f["status"]))
    else:
        # Default: cancelled orders do not count toward performance.
        q = q.filter((FactSale.order_status.is_(None)) | (FactSale.order_status != "Cancelled"))
    return q


AGG = [
    func.coalesce(func.sum(FactSale.revenue), 0).label("revenue"),
    func.coalesce(func.sum(FactSale.profit), 0).label("profit"),
    func.count(func.distinct(FactSale.order_id)).label("orders"),
    func.coalesce(func.sum(FactSale.quantity), 0).label("units"),
]


def kpi_row(db: Session, f: dict, d_from: date | None, d_to: date | None) -> dict:
    r = filtered(db, f, d_from, d_to).with_entities(*AGG).first()
    revenue, profit, orders, units = (to_float(r[0]), to_float(r[1]), int(r[2]), to_float(r[3]))
    row = pack_kpi_row(revenue, profit, orders, units)
    # Public contract keeps margin/aov as floats (0.0 when undefined) for
    # stable sorting; margin_or_none/aov_or_none available for N/A display.
    return {
        "revenue": row["revenue"],
        "profit": row["profit"],
        "margin": row["margin"],
        "margin_or_none": row["margin_or_none"],
        "orders": row["orders"],
        "units": row["units"],
        "aov": row["aov"],
        "aov_or_none": row["aov_or_none"],
    }


def growth(cur: float, prev: float | None) -> float | None:
    """Delegates to kpi_catalog.growth (single source of truth)."""
    return catalog_growth(cur, prev)


def first_order_subquery(db: Session):
    return (
        db.query(FactSale.customer_key.label("ck"), func.min(FactSale.date_key).label("first_key"))
        .filter(FactSale.is_deleted.is_(False), FactSale.customer_key.is_not(None))
        .group_by(FactSale.customer_key)
        .subquery()
    )


def customer_metrics(db: Session, f: dict, cf: date | None, ct: date | None) -> dict:
    """New vs returning computed against FIRST-EVER order (unfiltered by dims except status default)."""
    base = filtered(db, f, cf, ct)
    in_period = {
        r[0] for r in base.with_entities(FactSale.customer_key).distinct() if r[0] is not None
    }
    if not in_period:
        return {"total": 0, "new": 0, "returning": 0, "repeat_rate": 0.0, "avg_revenue": 0.0}
    sub = first_order_subquery(db)
    firsts = {ck: fk for ck, fk in db.query(sub.c.ck, sub.c.first_key).all() if ck in in_period}
    start_key = int(cf.strftime("%Y%m%d")) if cf else None
    new = sum(1 for ck in in_period if start_key is None or (firsts.get(ck) or 0) >= start_key)
    returning = len(in_period) - new
    rev = base.with_entities(func.coalesce(func.sum(FactSale.revenue), 0)).scalar() or 0
    total = len(in_period)
    return {
        "total": total,
        "new": new,
        "returning": returning,
        "repeat_rate": catalog_repeat_rate(returning, total),
        "avg_revenue": to_float(rev) / total if total else 0.0,
    }
