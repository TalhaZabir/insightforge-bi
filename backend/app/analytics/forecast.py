"""Baseline revenue forecasting — deterministic, no ML deps.

Workflow:
1. Aggregate filtered facts to monthly revenue (gap-filled with 0 + flagged).
2. Require >= 12 usable months, else return insufficient-history.
3. Chronological 80/20 train/validation split (never random).
4. Candidates: naive (last train value), seasonal-naive (same month prior
   year), moving-average(3). Pick lowest WAPE on validation.
5. Refit winner on full history; forecast `horizon` months ahead.
Metrics: MAE, RMSE, WAPE (None when denominator invalid). MAPE avoided
because actuals may be zero.
"""

from __future__ import annotations

import math
from datetime import date

from sqlalchemy.orm import Session

from app.analytics.filters import filtered
from app.models.entities import DimDate, FactSale


def _monthly_series(db: Session, f: dict, cf: date | None, ct: date | None):
    rows = (
        filtered(db, f, cf, ct)
        .join(DimDate, DimDate.date_key == FactSale.date_key)
        .with_entities(DimDate.year, DimDate.month, FactSale.revenue)
        .all()
    )
    by_ym: dict[str, float] = {}
    for y, m, rev in rows:
        if y is None or m is None:
            continue
        ym = f"{int(y):04d}-{int(m):02d}"
        by_ym[ym] = by_ym.get(ym, 0.0) + float(rev or 0)
    if not by_ym:
        return [], []
    months = sorted(by_ym)
    # gap-fill between first and last
    y0, m0 = int(months[0][:4]), int(months[0][5:7])
    y1, m1 = int(months[-1][:4]), int(months[-1][5:7])
    full, incomplete = [], []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        ym = f"{y:04d}-{m:02d}"
        full.append(ym)
        if ym not in by_ym:
            incomplete.append(ym)
        m += 1
        if m > 12:
            m, y = 1, y + 1
    values = [round(by_ym.get(ym, 0.0), 2) for ym in full]
    return full, values


def _mae(a: list[float], b: list[float]) -> float | None:
    if not a:
        return None
    return sum(abs(x - y) for x, y in zip(a, b, strict=True)) / len(a)


def _rmse(a: list[float], b: list[float]) -> float | None:
    if not a:
        return None
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)) / len(a))


def _wape(a: list[float], b: list[float]) -> float | None:
    denom = sum(abs(x) for x in a)
    if not denom:
        return None
    return sum(abs(x - y) for x, y in zip(a, b, strict=True)) / denom * 100.0


def _add_months(ym: str, n: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    m += n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}"


def forecast_revenue(
    db: Session, f: dict, cf: date | None, ct: date | None, horizon: int = 3
) -> dict:
    horizon = max(1, min(horizon, 12))
    labels, values = _monthly_series(db, f, cf, ct)
    if len(values) < 12:
        return {
            "available": False,
            "reason": f"Insufficient history: {len(values)} months available, 12 required.",
            "history": [{"month": m, "revenue": v} for m, v in zip(labels, values, strict=True)],
            "horizon": horizon,
        }
    n = len(values)
    split = max(8, int(n * 0.8))
    train, val = values[:split], values[split:]
    val_labels = labels[split:]

    def _naive() -> list[float]:
        return [train[-1]] * len(val)

    def _seasonal() -> list[float] | None:
        if len(train) < 12:
            return None
        out = []
        for i in range(len(val)):
            idx = len(train) - 12 + (i % 12)
            out.append(train[idx] if idx >= 0 else train[-1])
        return out

    def _ma3() -> list[float]:
        out = []
        hist = list(train)
        for _ in val:
            w = hist[-3:] if len(hist) >= 3 else hist
            out.append(sum(w) / len(w))
            # walk-forward with actual would leak; use naive step: keep hist fixed
        return out

    cands: dict[str, list[float] | None] = {
        "naive": _naive(),
        "seasonal_naive": _seasonal(),
        "moving_average_3": _ma3(),
    }
    scored = []
    for name, pred in cands.items():
        if not pred:
            continue
        scored.append((name, pred, _wape(val, pred)))
    scored.sort(key=lambda t: (t[2] is None, t[2] if t[2] is not None else 0))
    best_name, best_pred, best_wape = scored[0]
    accuracy = {
        "model": best_name,
        "mae": _mae(val, best_pred),
        "rmse": _rmse(val, best_pred),
        "wape": best_wape,
        "validation_months": len(val),
        "compared": [{"model": nm, "wape": w} for nm, _, w in scored],
    }
    # refit on full history
    full = list(values)
    preds: list[float] = []
    if best_name == "naive":
        preds = [full[-1]] * horizon
    elif best_name == "seasonal_naive":
        for i in range(horizon):
            idx = len(full) - 12 + (i % 12)
            preds.append(full[idx] if idx >= 0 else full[-1])
    else:
        w = full[-3:] if len(full) >= 3 else full
        avg = sum(w) / len(w)
        preds = [round(avg, 2)] * horizon
    last = labels[-1]
    future = [
        {"month": _add_months(last, i + 1), "revenue": round(p, 2)} for i, p in enumerate(preds)
    ]
    return {
        "available": True,
        "history": [{"month": m, "revenue": v} for m, v in zip(labels, values, strict=True)],
        "validation": {
            "months": val_labels,
            "actual": val,
            "predicted": [round(p, 2) for p in best_pred],
        },
        "accuracy": accuracy,
        "forecast": future,
        "horizon": horizon,
        "assumptions": "Monthly grain, gap months filled with 0, chronological 80/20 split, "
        "winner by lowest WAPE; refit on full history. No seasonality claim beyond "
        "seasonal-naive candidate.",
    }
