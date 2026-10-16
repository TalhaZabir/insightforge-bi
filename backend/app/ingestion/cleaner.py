"""Cleaning: transparent, configurable, never silently drops data."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.ingestion.aliases import CATEGORY_MAP, REGION_MAP, STATUS_MAP


@dataclass
class CleanOutcome:
    cleaned: pd.DataFrame
    rejected: pd.DataFrame  # original mapped rows + _rejection_reasons
    duplicates: pd.DataFrame  # removed exact-duplicate rows
    transformations: list[dict] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _track(outcome: CleanOutcome, step: str, affected: int, detail: str = ""):
    if affected:
        outcome.transformations.append(
            {"step": step, "affected_rows": int(affected), "detail": detail}
        )


def clean(df: pd.DataFrame, report) -> CleanOutcome:
    out = CleanOutcome(cleaned=pd.DataFrame(), rejected=pd.DataFrame(), duplicates=pd.DataFrame())
    if len(df) == 0:
        out.summary = {
            "valid_rows": 0,
            "rows_cleaned": 0,
            "duplicates_removed": 0,
            "rejected_rows": 0,
            "revenue_total": 0.0,
        }
        return out

    reasons: dict[int, list[str]] = {}
    for iss in report.issues:
        if iss["severity"] == "error":
            reasons.setdefault(iss["row_num"], []).append(f"{iss['rule']}: {iss['message']}")

    rej_idx = set(report.error_idx)
    dupe_idx = set(report.dupe_idx) - rej_idx
    valid = df[~df.index.isin(rej_idx | dupe_idx)].copy()

    out.duplicates = df.loc[sorted(dupe_idx)].copy() if dupe_idx else pd.DataFrame()
    rej = df.loc[sorted(rej_idx)].copy() if rej_idx else pd.DataFrame()
    if len(rej):
        rej["_rejection_reasons"] = rej["_row_num"].map(
            lambda r: "; ".join(reasons.get(int(r), []))
        )
    out.rejected = rej

    if len(valid) == 0:
        out.summary = {
            "valid_rows": 0,
            "rows_cleaned": 0,
            "duplicates_removed": len(out.duplicates),
            "rejected_rows": len(rej),
            "revenue_total": 0.0,
        }
        return out

    before = valid.copy()
    changed = pd.Series(False, index=valid.index)

    def mark(mask):
        changed.loc[mask[mask].index] |= True

    # 1. trim whitespace
    for c in valid.columns:
        if valid[c].dtype == object and not c.startswith("_"):
            stripped = valid[c].astype(str).str.strip()
            # keep NaN-ish: only where original was a string
            mask = valid[c].astype(str) != stripped
            valid.loc[mask[mask].index, c] = stripped[mask]
            mark(mask)

    # 1b. spreadsheet formula-injection guard: neutralize cells starting with
    # =, +, -, @, tab/CR (after whitespace strip) in free-text columns.
    formula_cols = [
        c
        for c in (
            "customer_name",
            "product_name",
            "order_id",
            "customer_id",
            "product_id",
            "region",
            "country",
            "category",
            "subcategory",
            "sales_channel",
            "sales_rep",
            "payment_method",
            "order_status",
        )
        if c in valid.columns
    ]
    inj = 0
    for c in formula_cols:
        series = valid[c].astype(str)
        mask = series.str.match(r"^[=+\-@\t\r]", na=False) & (valid[c].astype(str) != "")
        # don't touch genuine NaN stringified as 'nan' unless it matches (it doesn't)
        fixed = "'" + series[mask]
        valid.loc[mask[mask].index, c] = fixed
        inj += int(mask.sum())
        mark(mask)
    _track(
        out,
        "neutralize_formulas",
        inj,
        "Cells starting with = + - @_TAB_CR prefixed with ' to block spreadsheet formula execution",
    )
    # 2. normalize vocab
    if "category" in valid.columns:
        mapped = valid["category"].astype(str).str.lower().map(CATEGORY_MAP)
        m = mapped.notna() & (valid["category"] != mapped)
        valid.loc[m[m].index, "category"] = mapped[m]
        _track(
            out, "normalize_category", int(m.sum()), "Alias categories mapped to canonical names"
        )
        mark(m)
    if "region" in valid.columns:
        low = valid["region"].astype(str)
        mapped = low.str.lower().map(REGION_MAP)
        m = mapped.notna() & (valid["region"] != mapped)
        valid.loc[m[m].index, "region"] = mapped[m]
        _track(out, "normalize_region", int(m.sum()), "Alias regions mapped to canonical names")
        mark(m)
    if "order_status" in valid.columns:
        mapped = valid["order_status"].astype(str).str.lower().map(STATUS_MAP)
        m = mapped.notna() & (valid["order_status"] != mapped)
        valid.loc[m[m].index, "order_status"] = mapped[m]
        _track(out, "normalize_status", int(m.sum()), "Order statuses standardized")
        mark(m)

    # 3. dates -> ISO
    if "order_date" in valid.columns:
        parsed = pd.to_datetime(valid["order_date"].astype(str), errors="coerce")
        iso = parsed.dt.strftime("%Y-%m-%d")
        m = valid["order_date"] != iso
        valid.loc[:, "order_date"] = iso
        _track(out, "parse_dates", int(m.sum()), "Dates parsed to ISO YYYY-MM-DD")
        mark(m)

    # 4. numerics: strip $, commas, % then convert
    for c in ["quantity", "unit_price", "discount", "cost", "shipping_cost", "revenue", "profit"]:
        if c not in valid.columns:
            continue
        raw = valid[c].astype(str).str.strip()
        num = pd.to_numeric(
            raw.str.replace(r"[$,\s]", "", regex=True).str.replace("%", "", regex=False),
            errors="coerce",
        )
        m = (raw != num.astype(str)) & num.notna()
        valid.loc[:, c] = num
        mark(m)
    _track(
        out,
        "convert_numerics",
        int(changed.sum()),
        "Currency symbols, thousand separators and % stripped; strings converted to numbers",
    )

    for c in ["cost", "shipping_cost"]:
        if c in valid.columns:
            blanks = valid[c].isna()
            valid.loc[blanks[blanks].index, c] = 0.0
            _track(out, f"default_{c}", int(blanks.sum()), "Blank values defaulted to 0")
            mark(blanks)

    # 5. discount 0-100 scale -> 0-1 fraction
    if "discount" in valid.columns:
        d = pd.to_numeric(valid["discount"], errors="coerce").fillna(0.0)
        if (d > 1).any() and (d <= 100).all():
            valid.loc[:, "discount"] = (d / 100.0).round(4)
            _track(
                out,
                "normalize_discount",
                int((d > 1).sum()),
                "Percent-scale discounts converted to fractions",
            )
            mark(d > 1)
        else:
            valid.loc[:, "discount"] = d
            mark(d.astype(str) != valid["discount"].astype(str))

    # 6. derive revenue / profit
    if "revenue" in valid.columns:
        r = pd.to_numeric(valid["revenue"], errors="coerce")
        need = r.isna()
        if "quantity" in valid.columns and "unit_price" in valid.columns:
            q = pd.to_numeric(valid["quantity"], errors="coerce")
            p = pd.to_numeric(valid["unit_price"], errors="coerce")
            disc = (
                pd.to_numeric(valid["discount"], errors="coerce").fillna(0.0)
                if "discount" in valid.columns
                else 0.0
            )
            derivable = need & q.notna() & p.notna()
            valid.loc[derivable[derivable].index, "revenue"] = (q * p * (1 - disc)).round(2)[
                derivable
            ]
            _track(
                out,
                "derive_revenue",
                int(derivable.sum()),
                "revenue = quantity * unit_price * (1 - discount)",
            )
            mark(derivable)
    if "profit" in valid.columns and "revenue" in valid.columns:
        r = pd.to_numeric(valid["revenue"], errors="coerce")
        c = (
            pd.to_numeric(valid["cost"], errors="coerce").fillna(0.0)
            if "cost" in valid.columns
            else 0.0
        )
        q = pd.to_numeric(valid["quantity"], errors="coerce")
        s = (
            pd.to_numeric(valid["shipping_cost"], errors="coerce").fillna(0.0)
            if "shipping_cost" in valid.columns
            else 0.0
        )
        p = pd.to_numeric(valid["profit"], errors="coerce")
        expected = (r - c * q - s).round(2)
        fix = p.isna() | ((p - expected).abs() > 0.05)
        ready = fix & r.notna() & q.notna()
        valid.loc[ready[ready].index, "profit"] = expected[ready]
        _track(
            out,
            "derive_profit",
            int(ready.sum()),
            "profit = revenue - cost*quantity - shipping_cost (missing or inconsistent values recomputed)",
        )
        mark(ready)

    out.cleaned = valid.reset_index(drop=True)

    # before/after examples (first 5 changed rows, changed fields only)
    shown = 0
    for idx in before.index:
        if shown >= 5 or not changed.loc[idx]:
            continue
        diff_before, diff_after = {}, {}
        for c in before.columns:
            if c.startswith("_"):
                continue
            b, a = before.loc[idx, c], valid.loc[idx, c]
            if str(b) != str(a):
                diff_before[c], diff_after[c] = b, a
        if diff_before:
            out.examples.append(
                {
                    "row_num": int(before.loc[idx, "_row_num"]),
                    "before": diff_before,
                    "after": diff_after,
                }
            )
            shown += 1

    rev = pd.to_numeric(out.cleaned["revenue"], errors="coerce").fillna(0.0)
    out.summary = {
        "valid_rows": len(out.cleaned),
        "rows_cleaned": int(changed.sum()),
        "duplicates_removed": len(out.duplicates),
        "rejected_rows": len(out.rejected),
        "revenue_total": round(float(rev.sum()), 2),
        "date_min": str(out.cleaned["order_date"].min()) if "order_date" in out.cleaned else None,
        "date_max": str(out.cleaned["order_date"].max()) if "order_date" in out.cleaned else None,
    }
    return out
