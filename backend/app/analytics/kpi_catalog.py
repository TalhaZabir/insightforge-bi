"""Centralized KPI dictionary — single source of truth.

Business definitions (see docs/analytics.md):
- Revenue (net sales) = sum(fact_sales.revenue); revenue already stored net of
  discounts (cleaner: qty * unit_price * (1 - discount)). Cancelled orders are
  excluded by default in ``filtered()``; callers may opt-in via status filter.
- COGS = sum(cost * quantity); total cost = COGS + shipping.
- Gross profit = sum(fact_sales.profit) = revenue - COGS - shipping.
- Margin = profit / revenue (None when revenue == 0, never averaged).
- Orders = count(distinct order_id); units = sum(quantity).
- AOV = revenue / orders (None when orders == 0).
- Growth = (cur - prev) / abs(prev) * 100 (None when prev is None or 0,
  including negative-baseline safe behavior via abs()).
- Margin delta = (cur_margin - prev_margin) * 100 in percentage points.
- Customers: total = distinct customer_key in period; new = first-ever order
  >= period start; returning = total - new; repeat_rate = returning/total*100
  (lifetime definition, labelled in UI); avg_revenue = revenue/total.
"""

from __future__ import annotations

from decimal import Decimal

KPI_DEFINITIONS: dict[str, str] = {
    "revenue": "Net sales = SUM(revenue); cancelled orders excluded by default.",
    "profit": "Gross profit = SUM(profit) = revenue - cost*qty - shipping.",
    "margin": "Profit margin = profit / revenue; None when revenue is 0.",
    "orders": "Distinct order_id count (not order lines).",
    "units": "SUM(quantity) for qualifying transactions.",
    "aov": "Average order value = revenue / orders; None when orders is 0.",
    "repeat_rate": "Returning / total active customers * 100 (lifetime first-purchase definition).",
    "revenue_growth": "Like-for-like (cur-prev)/|prev|*100; None without valid baseline.",
    "profit_growth": "Like-for-like (cur-prev)/|prev|*100; None without valid baseline.",
}

LOW_MARGIN_THRESHOLD = 0.10

# Sentinel for "insufficient history" — API returns None, UI renders N/A.


def to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def margin(profit: float, revenue: float) -> float | None:
    """Weighted margin. Returns None when revenue is 0 (UI shows N/A)."""
    if not revenue:
        return None
    return profit / revenue


def margin_or_zero(profit: float, revenue: float) -> float:
    """Legacy-safe margin for grouped rows where 0.0 keeps sorting stable."""
    m = margin(profit, revenue)
    return m if m is not None else 0.0


def aov(revenue: float, orders: int) -> float | None:
    if not orders:
        return None
    return revenue / orders


def aov_or_zero(revenue: float, orders: int) -> float:
    v = aov(revenue, orders)
    return v if v is not None else 0.0


def growth(cur: float, prev: float | None) -> float | None:
    """Like-for-like growth %. None when baseline missing or zero."""
    if prev is None or prev == 0:
        return None
    return (cur - prev) / abs(prev) * 100.0


def margin_delta_pp(cur_margin: float | None, prev_margin: float | None) -> float | None:
    if cur_margin is None or prev_margin is None:
        return None
    return (cur_margin - prev_margin) * 100.0


def repeat_rate(returning: int, total: int) -> float:
    if not total:
        return 0.0
    return returning / total * 100.0


def is_low_margin(m: float | None, revenue: float) -> bool:
    return revenue > 0 and (m if m is not None else 0.0) < LOW_MARGIN_THRESHOLD


def pack_kpi_row(revenue: float, profit: float, orders: int, units: float) -> dict:
    return {
        "revenue": revenue,
        "profit": profit,
        "margin": margin_or_zero(profit, revenue),
        "margin_or_none": margin(profit, revenue),
        "orders": orders,
        "units": units,
        "aov": aov_or_zero(revenue, orders),
        "aov_or_none": aov(revenue, orders),
    }
