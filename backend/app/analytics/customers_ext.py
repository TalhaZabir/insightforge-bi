"""RFM segmentation + monthly cohort retention (deterministic, documented).

RFM scoring (within the current filter context):
- Recency: days from period-end (or latest sale) to last purchase. Lower = better.
- Frequency: distinct orders. Higher = better.
- Monetary: revenue. Higher = better.
Each dimension scored 1..5 by quintile (qcut; rank fallback on ties).
Label by total score: >=13 Champions, >=10 Loyal, >=7 Potential, >=5 At-risk,
else Lost/Hibernating.

Cohorts: acquisition month = first-EVER qualifying purchase (status default).
Retention[cohort][age] = active_in_month / cohort_size. Future/incomplete
cells are None (not 0); 0 means no activity in an observable month.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analytics.filters import filtered
from app.models.entities import DimCustomer, DimDate, FactSale


def _per_customer(db: Session, f: dict, cf: date | None, ct: date | None) -> list[dict]:
    # filtered() already outer-joins DimCustomer; only DimDate needs joining.
    q = (
        filtered(db, f, cf, ct)
        .join(DimDate, DimDate.date_key == FactSale.date_key)
        .with_entities(
            DimCustomer.customer_id,
            DimCustomer.customer_name,
            DimCustomer.segment,
            func.count(func.distinct(FactSale.order_id)).label("orders"),
            func.coalesce(func.sum(FactSale.revenue), 0).label("revenue"),
            func.coalesce(func.sum(FactSale.profit), 0).label("profit"),
            func.max(DimDate.date).label("last_date"),
            func.min(DimDate.date).label("first_in_period"),
        )
        .group_by(DimCustomer.customer_id, DimCustomer.customer_name, DimCustomer.segment)
    )
    rows = []
    for r in q.all():
        rows.append(
            {
                "customer_id": r[0],
                "customer_name": r[1],
                "segment": r[2],
                "orders": int(r[3]),
                "revenue": float(r[4] or 0),
                "profit": float(r[5] or 0),
                "last_date": r[6],
                "first_in_period": r[7],
            }
        )
    return rows


def _quintile_scores(values: list[float], higher_better: bool = True) -> list[int]:
    """1..5 scores. Equal values share the same score (rank-based, deterministic)."""
    n = len(values)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: values[i], reverse=higher_better)
    scores = [0] * n
    for rank, idx in enumerate(order):
        # rank 0 = best -> 5, rank n-1 = worst -> 1
        quint = 5 - (rank * 5 // max(n, 1))
        scores[idx] = max(1, min(5, quint))
    return scores


def _label(total: int) -> str:
    if total >= 13:
        return "Champions"
    if total >= 10:
        return "Loyal"
    if total >= 7:
        return "Potential"
    if total >= 5:
        return "At-risk"
    return "Hibernating"


def rfm(db: Session, f: dict, cf: date | None, ct: date | None) -> dict:
    rows = [r for r in _per_customer(db, f, cf, ct) if r["customer_id"]]
    if not rows:
        return {"customers": [], "segments": [], "scoring": _scoring_doc()}
    ref = ct or max((r["last_date"] for r in rows if r["last_date"]), default=None)
    recency_days = []
    for r in rows:
        if r["last_date"] and ref:
            recency_days.append((ref - r["last_date"]).days)
        else:
            recency_days.append(9999)
    r_scores = _quintile_scores([float(d) for d in recency_days], higher_better=False)
    f_scores = _quintile_scores([float(r["orders"]) for r in rows], higher_better=True)
    m_scores = _quintile_scores([r["revenue"] for r in rows], higher_better=True)
    for r, rs, fs, ms in zip(rows, r_scores, f_scores, m_scores, strict=True):
        total = rs + fs + ms
        r.update({"r": rs, "f": fs, "m": ms, "rfm_score": total, "rfm_label": _label(total)})
    agg: dict[str, dict] = {}
    for r in rows:
        a = agg.setdefault(
            r["rfm_label"], {"label": r["rfm_label"], "customers": 0, "revenue": 0.0}
        )
        a["customers"] += 1
        a["revenue"] += r["revenue"]
    segments = sorted(agg.values(), key=lambda a: a["revenue"], reverse=True)
    top = sorted(rows, key=lambda r: (r["rfm_score"], r["revenue"]), reverse=True)[:25]
    return {"customers": top, "segments": segments, "scoring": _scoring_doc()}


def _scoring_doc() -> dict:
    return {
        "method": "Quintile R/F/M scores 1..5 within current filters; "
        "Recency = days from period-end to last purchase (lower is better).",
        "labels": "Champions(13-15), Loyal(10-12), Potential(7-9), At-risk(5-6), Hibernating(3-4).",
    }


def cohorts(db: Session, f: dict, cf: date | None, ct: date | None, max_age: int = 11) -> dict:
    """Monthly acquisition cohorts with retention matrix."""
    # first-ever purchase per customer (status-default scope)
    firsts = (
        db.query(FactSale.customer_key, func.min(FactSale.date_key).label("fk"))
        .filter(FactSale.is_deleted.is_(False), FactSale.customer_key.is_not(None))
        .group_by(FactSale.customer_key)
        .subquery()
    )
    rows = (
        filtered(db, f, cf, ct)
        .join(DimDate, DimDate.date_key == FactSale.date_key)
        .outerjoin(firsts, firsts.c.customer_key == FactSale.customer_key)
        .with_entities(
            DimCustomer.customer_id,
            firsts.c.fk,
            DimDate.date,
        )
        .all()
    )
    if not rows:
        return {"cohorts": [], "note": "No customers in selection."}
    from datetime import date as _date

    def _ym(d) -> str:
        dd = d if isinstance(d, _date) else _date.fromisoformat(str(d))
        return f"{dd.year:04d}-{dd.month:02d}"

    def _key_to_ym(k: int) -> str:
        s = f"{int(k):08d}"
        return f"{s[:4]}-{s[4:6]}"

    def _add_months(ym: str, n: int) -> str:
        y, m = int(ym[:4]), int(ym[5:7])
        m += n
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        return f"{y:04d}-{m:02d}"

    # cohort per customer + active months
    cust_cohort: dict[str, str] = {}
    cust_months: dict[str, set[str]] = {}
    for cid, fk, d in rows:
        if not cid or d is None:
            continue
        cym = _key_to_ym(fk) if fk else _ym(d)
        if cid not in cust_cohort or cym < cust_cohort[cid]:
            cust_cohort[cid] = cym
        cust_months.setdefault(cid, set()).add(_ym(d))
    by_cohort: dict[str, list[str]] = {}
    for cid, cym in cust_cohort.items():
        by_cohort.setdefault(cym, []).append(cid)
    # observable months = months present in filtered data
    all_months = sorted({m for s in cust_months.values() for m in s})
    latest = all_months[-1] if all_months else None
    out = []
    for cym in sorted(by_cohort)[:24]:
        members = by_cohort[cym]
        size = len(members)
        cells: list[float | None] = []
        for age in range(max_age + 1):
            m = _add_months(cym, age)
            if latest and m > latest:
                cells.append(None)  # incomplete / future
                continue
            active = sum(1 for cid in members if m in cust_months.get(cid, set()))
            cells.append(round(active / size, 4) if size else None)
        out.append({"cohort": cym, "size": size, "retention": cells})
    return {
        "cohorts": out,
        "note": "Retention = active members / cohort size. null = incomplete month, 0 = no activity.",
    }


def declining(
    db: Session, f: dict, cf: date | None, ct: date | None, limit: int = 10
) -> list[dict]:
    """Customers whose second-half revenue < 70% of first-half (needs dated range)."""
    if not cf or not ct or ct <= cf:
        return []
    mid_ord = (cf.toordinal() + ct.toordinal()) // 2
    from datetime import date as _date

    mid = _date.fromordinal(mid_ord)
    rows = (
        filtered(db, f, cf, ct)
        .join(DimDate, DimDate.date_key == FactSale.date_key)
        .with_entities(
            DimCustomer.customer_id,
            DimCustomer.customer_name,
            DimDate.date,
            FactSale.revenue,
        )
        .all()
    )
    agg: dict[str, dict] = {}
    for cid, cname, d, rev in rows:
        if not cid or d is None:
            continue
        a = agg.setdefault(
            cid, {"customer_id": cid, "customer_name": cname, "first_half": 0.0, "second_half": 0.0}
        )
        if d <= mid:
            a["first_half"] += float(rev or 0)
        else:
            a["second_half"] += float(rev or 0)
    out = []
    for a in agg.values():
        if a["first_half"] > 0 and a["second_half"] < 0.7 * a["first_half"]:
            a["decline_pct"] = (a["second_half"] - a["first_half"]) / a["first_half"] * 100.0
            out.append(a)
    return sorted(out, key=lambda a: a["decline_pct"])[:limit]
