"""Deterministic insights: every statement traces to a computed metric. No LLM, no fabrication."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.analytics import forecast as FC
from app.analytics import queries as Q
from app.analytics.filters import customer_metrics, growth, kpi_row
from app.analytics.kpi_catalog import margin_delta_pp
from app.models.entities import ImportJob


def thresholds() -> dict:
    """Configurable via env (see docs/analytics.md); defaults are documented."""

    def _f(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except ValueError:
            return default

    return {
        "revenue_warn_pct": _f("INS_REVENUE_WARN_PCT", -10.0),
        "margin_move_pp": _f("INS_MARGIN_MOVE_PP", 0.5),
        "margin_warn_pp": _f("INS_MARGIN_WARN_PP", -2.0),
        "region_growth_pct": _f("INS_REGION_GROWTH_PCT", 5.0),
        "region_min_share": _f("INS_REGION_MIN_SHARE", 0.05),
        "region_opportunity_share": _f("INS_REGION_OPP_SHARE", 0.08),
        "category_growth_pct": _f("INS_CATEGORY_GROWTH_PCT", 15.0),
        "category_min_share": _f("INS_CATEGORY_MIN_SHARE", 0.10),
        "repeat_move_pp": _f("INS_REPEAT_MOVE_PP", 2.0),
        "discount_gap_pp": _f("INS_DISCOUNT_GAP_PP", 5.0),
        "concentration_warn": _f("INS_CONCENTRATION_WARN", 0.30),
        "concentration_crit": _f("INS_CONCENTRATION_CRIT", 0.50),
        "reject_warn_pct": _f("INS_REJECT_WARN_PCT", 2.0),
        "reject_crit_pct": _f("INS_REJECT_CRIT_PCT", 5.0),
        "target_warn_pct": _f("INS_TARGET_WARN_PCT", -10.0),
        "forecast_warn_pct": _f("INS_FORECAST_WARN_PCT", -10.0),
    }


def _ins(
    category,
    severity,
    headline,
    explanation,
    metric,
    action,
    dimension=None,
    observed=None,
    baseline=None,
    abs_change=None,
    pct_change=None,
    scope=None,
    calculation=None,
    limitations=None,
):
    return {
        "category": category,
        "severity": severity,
        "headline": headline,
        "explanation": explanation,
        "metric": metric,
        "action": action,
        "dimension": dimension,
        "observed": observed,
        "baseline": baseline,
        "abs_change": abs_change,
        "pct_change": pct_change,
        "scope": scope,
        "calculation": calculation,
        "limitations": limitations,
    }


def _pct(v):
    return {"label": "percent", "value": round(v, 1), "unit": "%"}


def generate(db: Session, f: dict, cf, ct, pf, pt) -> list[dict]:
    T = thresholds()
    out: list[dict] = []
    scope = {k: v for k, v in (f or {}).items() if v}
    cur, prev = kpi_row(db, f, cf, ct), (kpi_row(db, f, pf, pt) if pf else None)
    if cur["orders"] == 0:
        return [
            _ins(
                "trend",
                "neutral",
                "No orders in the selected period",
                "No fact rows match the current filters. Widen the date range or clear filters.",
                {"label": "orders", "value": 0, "unit": "count"},
                "Clear filters or import data for this period.",
                None,
            )
        ]

    # 1. revenue trend
    if prev:
        g = growth(cur["revenue"], prev["revenue"])
        if g is not None:
            sev = "positive" if g >= 0 else ("warning" if g > T["revenue_warn_pct"] else "critical")
            out.append(
                _ins(
                    "trend",
                    sev,
                    f"Revenue {'grew' if g >= 0 else 'declined'} {abs(g):.1f}% vs the previous period",
                    f"Current {cur['revenue']:,.0f} vs previous {prev['revenue']:,.0f}.",
                    {"label": "Revenue growth", "value": round(g, 1), "unit": "%"},
                    "Double down on what worked."
                    if g >= 0
                    else "Review underperforming regions and products below.",
                    None,
                    observed=round(cur["revenue"], 2),
                    baseline=round(prev["revenue"], 2),
                    abs_change=round(cur["revenue"] - prev["revenue"], 2),
                    pct_change=round(g, 1),
                    scope=scope or None,
                    calculation="(cur-prev)/|prev|*100 on net revenue, like-for-like period length.",
                    limitations=None if prev["revenue"] else "Baseline is zero; growth undefined.",
                )
            )
        # 2. margin move
        dpp = margin_delta_pp(cur["margin"], prev["margin"])
        if dpp is not None and abs(dpp) >= T["margin_move_pp"]:
            sev = (
                "positive" if dpp > 0 else ("warning" if dpp > T["margin_warn_pp"] else "critical")
            )
            out.append(
                _ins(
                    "trend",
                    sev,
                    f"Profit margin {'expanded' if dpp > 0 else 'contracted'} by {abs(dpp):.1f}pp",
                    f"Margin moved from {prev['margin'] * 100:.1f}% to {cur['margin'] * 100:.1f}%.",
                    {"label": "Margin change", "value": round(dpp, 1), "unit": "pp"},
                    "Protect pricing power." if dpp > 0 else "Audit discounts and high-cost lines.",
                    None,
                )
            )

    # 3-4. regions
    regs = Q.by_region(db, f, cf, ct, pf, pt)
    grown = [r for r in regs if r.get("revenue_growth") is not None]
    total_reg = sum(r["revenue"] for r in regs) or 1
    if grown:
        best = max(grown, key=lambda r: r["revenue_growth"])
        if (
            best["revenue_growth"] > T["region_growth_pct"]
            and best["revenue"] / total_reg >= T["region_opportunity_share"]
        ):
            out.append(
                _ins(
                    "opportunity",
                    "positive",
                    f"{best['region']} is outperforming (+{best['revenue_growth']:.1f}%)",
                    f"{best['region']} generated {best['revenue']:,.0f} revenue with "
                    f"{best['margin'] * 100:.1f}% margin.",
                    {
                        "label": f"{best['region']} growth",
                        "value": round(best["revenue_growth"], 1),
                        "unit": "%",
                    },
                    f"Replicate {best['region']}'s channel mix elsewhere.",
                    {"type": "region", "value": best["region"]},
                )
            )
        weak = [r for r in grown if r["revenue_growth"] < -T["region_growth_pct"]]
        total = sum(r["revenue"] for r in regs) or 1
        for r in sorted(weak, key=lambda x: x["revenue_growth"])[:2]:
            if r["revenue"] / total >= T["region_min_share"]:
                out.append(
                    _ins(
                        "risk",
                        "warning",
                        f"{r['region']} is underperforming ({r['revenue_growth']:.1f}%)",
                        f"{r['region']} holds {r['revenue'] / total * 100:.1f}% of revenue and is shrinking.",
                        {
                            "label": f"{r['region']} growth",
                            "value": round(r["revenue_growth"], 1),
                            "unit": "%",
                        },
                        f"Investigate pricing, assortment and coverage in {r['region']}.",
                        {"type": "region", "value": r["region"]},
                    )
                )

    # 5. high-revenue, low-margin products
    prods = Q.by_product(db, f, cf, ct, limit=100)
    risky = [p for p in prods if p["low_margin"]]
    for p in sorted(risky, key=lambda x: x["revenue"], reverse=True)[:2]:
        out.append(
            _ins(
                "risk",
                "warning",
                f"{p['product_name']} earns {p['revenue']:,.0f} at {p['margin'] * 100:.1f}% margin",
                f"High revenue but margin below 10% ({p['units']:,.0f} units).",
                {"label": "Product margin", "value": round(p["margin"] * 100, 1), "unit": "%"},
                "Raise price, cut cost, or reduce discount on this SKU.",
                {"type": "product", "value": p["product_id"]},
            )
        )

    # 6. fastest-growing category (needs material share to avoid small-base noise)
    cats = Q.by_category(db, f, cf, ct, pf, pt)
    total_cat = sum(c["revenue"] for c in cats) or 1
    grown_cats = [
        c
        for c in cats
        if c.get("revenue_growth") is not None
        and c["revenue_growth"] > T["category_growth_pct"]
        and c["revenue"] / total_cat >= T["category_min_share"]
    ]
    if grown_cats:
        c = max(grown_cats, key=lambda x: x["revenue_growth"])
        out.append(
            _ins(
                "opportunity",
                "positive",
                f"{c['category']} is growing fast (+{c['revenue_growth']:.1f}%)",
                f"Category revenue {c['revenue']:,.0f} at {c['margin'] * 100:.1f}% margin.",
                {
                    "label": f"{c['category']} growth",
                    "value": round(c["revenue_growth"], 1),
                    "unit": "%",
                },
                f"Increase inventory and marketing for {c['category']}.",
                {"type": "category", "value": c["category"]},
            )
        )

    # 7. repeat rate move
    cm_cur = customer_metrics(db, f, cf, ct)
    if pf:
        cm_prev = customer_metrics(db, f, pf, pt)
        d = cm_cur["repeat_rate"] - cm_prev["repeat_rate"]
        if abs(d) >= T["repeat_move_pp"]:
            out.append(
                _ins(
                    "trend",
                    "positive" if d > 0 else "warning",
                    f"Repeat-customer rate {'rose' if d > 0 else 'fell'} to "
                    f"{cm_cur['repeat_rate']:.1f}%",
                    f"Returning {cm_cur['returning']} of {cm_cur['total']} customers "
                    f"(was {cm_prev['repeat_rate']:.1f}%).",
                    {"label": "Repeat-rate change", "value": round(d, 1), "unit": "pp"},
                    "Strengthen retention offers."
                    if d <= 0
                    else "Keep the loyalty mechanics that are working.",
                    None,
                )
            )
    elif cm_cur["total"] > 0 and cm_cur["repeat_rate"] < 20:
        out.append(
            _ins(
                "risk",
                "neutral",
                f"Repeat-customer rate is low at {cm_cur['repeat_rate']:.1f}%",
                f"Only {cm_cur['returning']} of {cm_cur['total']} customers bought before.",
                _pct(cm_cur["repeat_rate"]),
                "Consider post-purchase follow-ups and bundles.",
                None,
            )
        )

    # 8. discount drag
    buckets = {b["bucket"]: b for b in Q.discount_buckets(db, f, cf, ct)}
    if "high" in buckets and "none" in buckets and buckets["high"]["orders"] >= 10:
        gap = (buckets["none"]["margin"] - buckets["high"]["margin"]) * 100.0
        if gap >= T["discount_gap_pp"]:
            out.append(
                _ins(
                    "risk",
                    "warning",
                    f"Heavily discounted orders earn {gap:.1f}pp less margin",
                    f"No-discount margin {buckets['none']['margin'] * 100:.1f}% vs "
                    f"high-discount {buckets['high']['margin'] * 100:.1f}% "
                    f"({buckets['high']['orders']} orders).",
                    {"label": "Discount margin gap", "value": round(gap, 1), "unit": "pp"},
                    "Cap discount depth on low-margin SKUs.",
                    None,
                )
            )

    # 9. concentration risk
    top = Q.top_customers(db, f, cf, ct, limit=3)
    if cur["revenue"] > 0:
        share = sum(t["revenue"] for t in top) / cur["revenue"]
        if share > T["concentration_warn"] and len(top) == 3:
            out.append(
                _ins(
                    "risk",
                    "critical" if share > T["concentration_crit"] else "warning",
                    f"Top 3 customers are {share * 100:.1f}% of revenue",
                    f"Concentration: {', '.join(t['customer_name'] or t['customer_id'] for t in top)}.",
                    {"label": "Top-3 concentration", "value": round(share * 100, 1), "unit": "%"},
                    "Diversify the customer base to reduce dependency.",
                    None,
                )
            )

    # 10. data quality
    job = (
        db.query(ImportJob)
        .filter(ImportJob.status == "confirmed")
        .order_by(ImportJob.created_at.desc())
        .first()
    )
    if job and job.stats and job.stats.get("validation"):
        v = job.stats["validation"]
        rate = (v["rejected_rows"] / v["total_rows"] * 100.0) if v["total_rows"] else 0
        if rate > T["reject_warn_pct"]:
            out.append(
                _ins(
                    "quality",
                    "critical" if rate > T["reject_crit_pct"] else "warning",
                    f"Latest import rejected {rate:.1f}% of rows",
                    f"{v['rejected_rows']} of {v['total_rows']} rows quarantined; "
                    f"{v.get('warnings', 0)} warnings. Treat affected cuts with caution.",
                    {"label": "Reject rate", "value": round(rate, 1), "unit": "%"},
                    "Download the rejection report and fix source data.",
                    None,
                )
            )

    # 11. target variance (single-month periods with a defined target)
    try:
        if cf and ct and cf.year == ct.year and cf.month == ct.month:
            from app.models.entities import MonthlyTarget as _MT

            _m = db.query(_MT).filter(_MT.month == cf.replace(day=1)).first()
            if _m and float(_m.revenue_target or 0) > 0:
                tgt = float(_m.revenue_target)
                var = growth(cur["revenue"], tgt)
                if var is not None and var <= T["target_warn_pct"]:
                    out.append(
                        _ins(
                            "risk",
                            "warning",
                            f"Revenue {var:.1f}% below {cf.strftime('%Y-%m')} target",
                            f"Actual {cur['revenue']:,.0f} vs target {tgt:,.0f}.",
                            {"label": "Target variance", "value": round(var, 1), "unit": "%"},
                            "Pull forward promotions or review pipeline coverage for the month.",
                            None,
                            observed=round(cur["revenue"], 2),
                            baseline=tgt,
                            abs_change=round(cur["revenue"] - tgt, 2),
                            pct_change=round(var, 1),
                            scope={"month": cf.strftime("%Y-%m")},
                            calculation="Actual month revenue vs MonthlyTarget.",
                            limitations="Unfiltered actuals; filters narrow the scope.",
                        )
                    )
    except Exception:
        pass  # targets table may not exist on old DBs; never break insights

    # 12. forecast risk (baseline forecast points down next month)
    try:
        fc = FC.forecast_revenue(db, f, cf, ct, horizon=1)
        if fc.get("available") and fc.get("forecast") and fc.get("history"):
            nxt = float(fc["forecast"][0]["revenue"])
            last = float(fc["history"][-1]["revenue"])
            if last > 0:
                chg = (nxt - last) / last * 100.0
                if chg <= T["forecast_warn_pct"]:
                    out.append(
                        _ins(
                            "risk",
                            "warning",
                            f"Baseline forecast points {abs(chg):.1f}% lower next month",
                            f"{fc.get('accuracy', {}).get('model', 'baseline')} model: "
                            f"{last:,.0f} → {nxt:,.0f}.",
                            {"label": "Forecast change", "value": round(chg, 1), "unit": "%"},
                            "Review inventory and demand drivers before the dip.",
                            None,
                            observed=nxt,
                            baseline=last,
                            abs_change=round(nxt - last, 2),
                            pct_change=round(chg, 1),
                            calculation="Winner of naive/seasonal-naive/MA(3) by WAPE on chronological holdout.",
                            limitations="Baseline only; no promotions/calendar effects.",
                        )
                    )
    except Exception:
        pass

    # dedupe by headline (stable, deterministic)
    seen: set[str] = set()
    deduped = []
    for i in out:
        if i["headline"] not in seen:
            seen.add(i["headline"])
            deduped.append(i)
    return deduped
