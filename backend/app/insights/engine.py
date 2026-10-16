"""Deterministic insights: every statement traces to a computed metric. No LLM, no fabrication."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.analytics import queries as Q
from app.analytics.filters import customer_metrics, growth, kpi_row
from app.models.entities import ImportJob


def _ins(category, severity, headline, explanation, metric, action, dimension=None):
    return {
        "category": category,
        "severity": severity,
        "headline": headline,
        "explanation": explanation,
        "metric": metric,
        "action": action,
        "dimension": dimension,
    }


def _pct(v):
    return {"label": "percent", "value": round(v, 1), "unit": "%"}


def generate(db: Session, f: dict, cf, ct, pf, pt) -> list[dict]:
    out: list[dict] = []
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
            sev = "positive" if g >= 0 else ("warning" if g > -10 else "critical")
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
                )
            )
        # 2. margin move
        dpp = (cur["margin"] - prev["margin"]) * 100.0
        if abs(dpp) >= 0.5:
            sev = "positive" if dpp > 0 else ("warning" if dpp > -2 else "critical")
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
        if best["revenue_growth"] > 5 and best["revenue"] / total_reg >= 0.08:
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
        weak = [r for r in grown if r["revenue_growth"] < -5]
        total = sum(r["revenue"] for r in regs) or 1
        for r in sorted(weak, key=lambda x: x["revenue_growth"])[:2]:
            if r["revenue"] / total >= 0.05:
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
        and c["revenue_growth"] > 15
        and c["revenue"] / total_cat >= 0.10
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
        if abs(d) >= 2:
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
        if gap >= 5:
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
        if share > 0.30 and len(top) == 3:
            out.append(
                _ins(
                    "risk",
                    "critical" if share > 0.5 else "warning",
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
        if rate > 2:
            out.append(
                _ins(
                    "quality",
                    "critical" if rate > 5 else "warning",
                    f"Latest import rejected {rate:.1f}% of rows",
                    f"{v['rejected_rows']} of {v['total_rows']} rows quarantined; "
                    f"{v.get('warnings', 0)} warnings. Treat affected cuts with caution.",
                    {"label": "Reject rate", "value": round(rate, 1), "unit": "%"},
                    "Download the rejection report and fix source data.",
                    None,
                )
            )
    return out
