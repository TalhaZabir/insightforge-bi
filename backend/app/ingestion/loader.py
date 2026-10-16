"""Confirm loader: cleaned rows -> dimensions + fact_sales (idempotent per batch)."""

from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from app.models.entities import (
    DimChannel,
    DimCustomer,
    DimDate,
    DimProduct,
    DimRegion,
    DimRep,
    FactSale,
    ImportJob,
)

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _get_or_create_date(db: Session, iso: str, cache: dict) -> int:
    key = int(iso.replace("-", ""))
    if key in cache:
        return cache[key]
    row = db.query(DimDate).filter(DimDate.date_key == key).first()
    if row is None:
        d = pd.to_datetime(iso).date()
        row = DimDate(
            date_key=key,
            date=d,
            year=d.year,
            quarter=(d.month - 1) // 3 + 1,
            month=d.month,
            month_name=MONTHS[d.month],
            day=d.day,
            weekday=d.weekday(),
            weekday_name=WEEKDAYS[d.weekday()],
            is_weekend=d.weekday() >= 5,
        )
        db.add(row)
        db.flush()
    cache[key] = row.date_key
    return row.date_key


def _get_or_create(db: Session, model, cache: dict, lookup: dict, defaults: dict):
    ckey = (model.__tablename__, tuple(sorted(lookup.items())))
    if ckey in cache:
        return cache[ckey]
    row = db.query(model).filter_by(**lookup).first()
    if row is None:
        row = model(**{**lookup, **defaults})
        db.add(row)
        db.flush()
    cache[ckey] = row.id
    return row.id


def load_cleaned_to_db(
    db: Session,
    job: ImportJob,
    cleaned: pd.DataFrame,
    import_mode: str = "append",
    confirm_replace: bool = False,
) -> dict:
    cache: dict = {}
    facts: list[FactSale] = []
    skipped_upsert = 0
    soft_deleted = 0

    if import_mode == "replace":
        if not confirm_replace:
            raise ValueError("replace mode requires confirm_replace=True")
        soft_deleted = (
            db.query(FactSale)
            .filter(FactSale.is_deleted.is_(False))
            .update({"is_deleted": True}, synchronize_session=False)
        )
        db.flush()

    existing_order_ids: set[str] = set()
    if import_mode == "upsert":
        existing_order_ids = {
            r[0]
            for r in db.query(FactSale.order_id)
            .filter(FactSale.is_deleted.is_(False))
            .distinct()
            .all()
        }

    def val(row, col: str, default=None):
        v = row.get(col, default)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return default
        if isinstance(v, str) and v.strip() == "":
            return default
        return v

    def fnum(row, col: str) -> float:
        v = val(row, col)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return 0.0
        try:
            f = float(v)
        except (TypeError, ValueError):
            return 0.0
        return 0.0 if pd.isna(f) else f

    for i, r in cleaned.iterrows():
        oid = str(r["order_id"])
        if import_mode == "upsert" and oid in existing_order_ids:
            skipped_upsert += 1
            continue
        date_key = _get_or_create_date(db, str(r["order_date"]), cache)
        cust = val(r, "customer_id")
        customer_key = (
            _get_or_create(
                db,
                DimCustomer,
                cache,
                {"customer_id": str(cust)},
                {"customer_name": val(r, "customer_name"), "segment": val(r, "customer_segment")},
            )
            if cust
            else None
        )
        prod = val(r, "product_id")
        product_key = (
            _get_or_create(
                db,
                DimProduct,
                cache,
                {"product_id": str(prod)},
                {
                    "product_name": val(r, "product_name"),
                    "category": val(r, "category"),
                    "subcategory": val(r, "subcategory"),
                },
            )
            if prod
            else None
        )
        region_key = None
        if val(r, "region"):
            region_key = _get_or_create(
                db,
                DimRegion,
                cache,
                {"region": str(val(r, "region")), "country": val(r, "country")},
                {},
            )
        channel_key = (
            _get_or_create(db, DimChannel, cache, {"channel": str(val(r, "sales_channel"))}, {})
            if val(r, "sales_channel")
            else None
        )
        rep_key = (
            _get_or_create(db, DimRep, cache, {"rep_name": str(val(r, "sales_rep"))}, {})
            if val(r, "sales_rep")
            else None
        )
        facts.append(
            FactSale(
                batch_id=job.batch_id,
                order_id=str(r["order_id"]),
                line_num=int(i) + 1,
                date_key=date_key,
                customer_key=customer_key,
                product_key=product_key,
                region_key=region_key,
                channel_key=channel_key,
                rep_key=rep_key,
                quantity=fnum(r, "quantity"),
                unit_price=fnum(r, "unit_price"),
                discount=fnum(r, "discount"),
                cost=fnum(r, "cost"),
                shipping_cost=fnum(r, "shipping_cost"),
                revenue=fnum(r, "revenue"),
                profit=fnum(r, "profit"),
                payment_method=val(r, "payment_method"),
                order_status=val(r, "order_status"),
            )
        )
        if len(facts) >= 1000:
            db.add_all(facts)
            db.flush()
            facts = []
    if facts:
        db.add_all(facts)
        db.flush()

    # completion summary from what was actually written
    rows = db.query(FactSale).filter(FactSale.batch_id == job.batch_id).all()
    revenues = [float(x.revenue or 0) for x in rows]
    dates = sorted({x.date_key for x in rows})
    return {
        "confirmed_rows": len(rows),
        "revenue_total": round(sum(revenues), 2),
        "date_min": str(dates[0]) if dates else None,
        "date_max": str(dates[-1]) if dates else None,
        "customers": len({x.customer_key for x in rows if x.customer_key}),
        "products": len({x.product_key for x in rows if x.product_key}),
        "regions": len({x.region_key for x in rows if x.region_key}),
        "import_mode": import_mode,
        "skipped_upsert": skipped_upsert,
        "soft_deleted": soft_deleted,
    }
