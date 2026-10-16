"""Analytics endpoints — all share filters + prev-period comparison."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics import queries as Q
from app.analytics.filters import (
    common_filters,
    customer_metrics,
    growth,
    kpi_row,
    resolve_period,
)
from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.entities import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _period(db: Session, f: dict):
    cf, ct, pf, pt = resolve_period(f)
    cur, prev = kpi_row(db, f, cf, ct), kpi_row(db, f, pf, pt) if pf else None
    return cf, ct, pf, pt, cur, prev


@router.get("/overview")
def overview(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    cf, ct, pf, pt, cur, prev = _period(db, f)
    cm = customer_metrics(db, f, cf, ct)
    kpis = {
        k: {
            "value": cur[k],
            "previous": prev[k] if prev else None,
            "growth_pct": growth(cur[k], prev[k]) if prev else None,
        }
        for k in ("revenue", "profit", "orders", "units", "aov")
    }
    kpis["margin"] = {
        "value": cur["margin"],
        "previous": prev["margin"] if prev else None,
        "delta_pp": ((cur["margin"] - prev["margin"]) * 100.0) if prev else None,
    }
    kpis["repeat_rate"] = {"value": cm["repeat_rate"], "previous": None, "growth_pct": None}
    kpis["revenue_growth"] = {"value": kpis["revenue"]["growth_pct"]}
    kpis["profit_growth"] = {"value": kpis["profit"]["growth_pct"]}
    return {
        "period": {
            "from": str(cf) if cf else None,
            "to": str(ct) if ct else None,
            "prev_from": str(pf) if pf else None,
            "prev_to": str(pt) if pt else None,
        },
        "kpis": kpis,
        "customers": cm,
        "trend": Q.timeseries(db, f, cf, ct),
        "by_region": Q.by_region(db, f, cf, ct, pf, pt)[:8],
        "by_category": Q.by_category(db, f, cf, ct, pf, pt),
    }


@router.get("/sales")
def sales(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    cf, ct, pf, pt, cur, prev = _period(db, f)
    return {
        "kpis": cur,
        "trend": Q.timeseries(db, f, cf, ct),
        "by_channel": Q.by_channel(db, f, cf, ct, pf, pt),
        "by_region": Q.by_region(db, f, cf, ct, pf, pt),
        "by_category": Q.by_category(db, f, cf, ct, pf, pt),
    }


@router.get("/sales/orders")
def sales_orders(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 25,
    sort: str = "order_date",
    direction: str = "desc",
    search: str | None = None,
):
    cf, ct, _, _ = resolve_period(f)
    return Q.orders_table(
        db,
        f,
        cf,
        ct,
        page=min(page, 1000),
        page_size=min(page_size, 100),
        sort=sort,
        direction=direction,
        search=search,
    )


@router.get("/profitability")
def profitability(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    cf, ct, pf, pt, cur, prev = _period(db, f)
    products = Q.by_product(db, f, cf, ct)
    return {
        "kpis": {
            **cur,
            "revenue_growth": growth(cur["revenue"], prev["revenue"]) if prev else None,
            "profit_growth": growth(cur["profit"], prev["profit"]) if prev else None,
        },
        "trend": Q.timeseries(db, f, cf, ct),
        "by_category": Q.by_category(db, f, cf, ct, pf, pt),
        "by_product": products[:20],
        "low_margin_products": [p for p in products if p["low_margin"]][:10],
        "discount_buckets": Q.discount_buckets(db, f, cf, ct),
    }


@router.get("/customers")
def customers(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    cf, ct, _, _, cur, _ = _period(db, f)
    cm = customer_metrics(db, f, cf, ct)
    top = Q.top_customers(db, f, cf, ct)
    total_rev = cur["revenue"]
    buckets = ["< $500", "$500–2k", "$2k–10k", "> $10k"]
    dist_customers = [0, 0, 0, 0]
    dist_revenue = [0.0, 0.0, 0.0, 0.0]
    full = Q.top_customers(db, f, cf, ct, limit=100000)
    for t in full:
        i = (
            0
            if t["revenue"] < 500
            else (1 if t["revenue"] < 2000 else (2 if t["revenue"] < 10000 else 3))
        )
        dist_customers[i] += 1
        dist_revenue[i] += t["revenue"]
    dist = [
        {"bucket": b, "customers": c, "revenue": r}
        for b, c, r in zip(buckets, dist_customers, dist_revenue, strict=True)
    ]
    return {
        "metrics": {**cm, "avg_order_value": cur["aov"]},
        "top_customers": top,
        "segment_mix": Q.segment_mix(db, f, cf, ct),
        "revenue_concentration_top3": (
            sum(t["revenue"] for t in top[:3]) / total_rev if total_rev else 0.0
        ),
        "revenue_distribution": dist,
    }


@router.get("/products")
def products(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    cf, ct, pf, pt, _cur, _prev = _period(db, f)
    prods = Q.by_product(db, f, cf, ct, limit=100)
    return {
        "best_sellers": sorted(prods, key=lambda r: r["units"], reverse=True)[:15],
        "highest_profit": sorted(prods, key=lambda r: r["profit"], reverse=True)[:15],
        "lowest_margin": sorted([p for p in prods if p["revenue"] > 0], key=lambda r: r["margin"])[
            :15
        ],
        "by_category": Q.by_category(db, f, cf, ct, pf, pt),
        "trend": Q.timeseries(db, f, cf, ct),
    }


@router.get("/regions")
def regions(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    cf, ct, pf, pt, _cur, _prev = _period(db, f)
    by_reg = Q.by_region(db, f, cf, ct, pf, pt)
    ranked = [{**r, "rank": i + 1} for i, r in enumerate(by_reg)]
    return {
        "ranking": ranked,
        "by_channel": Q.by_channel(db, f, cf, ct, pf, pt),
        "trend": Q.timeseries(db, f, cf, ct),
    }


@router.get("/facets")
def facets(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    """Distinct filter values present in the data (nulls excluded)."""
    from app.models.entities import (
        DimChannel,
        DimCustomer,
        DimProduct,
        DimRegion,
        DimRep,
        FactSale,
    )

    def distinct(model, col):
        return sorted(r[0] for r in db.query(col).distinct().all() if r[0])

    return {
        "regions": distinct(DimRegion, DimRegion.region),
        "countries": distinct(DimRegion, DimRegion.country),
        "categories": distinct(DimProduct, DimProduct.category),
        "subcategories": distinct(DimProduct, DimProduct.subcategory),
        "channels": distinct(DimChannel, DimChannel.channel),
        "segments": distinct(DimCustomer, DimCustomer.segment),
        "reps": distinct(DimRep, DimRep.rep_name),
        "statuses": distinct(FactSale, FactSale.order_status),
    }
