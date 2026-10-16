"""Row-level validation: hard errors vs soft warnings, with full stats."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from app.ingestion.aliases import CATEGORY_MAP, REGION_MAP, STATUS_MAP

DATE_MIN = date(2000, 1, 1)


@dataclass
class ValidationReport:
    issues: list[dict] = field(default_factory=list)  # {row_num, severity, rule, column, message}
    error_idx: set = field(default_factory=set)  # dataframe index labels with >=1 error
    dupe_idx: set = field(default_factory=set)  # exact-duplicate rows beyond first (valid only)
    stats: dict = field(default_factory=dict)


def _is_blank(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""


def _num(s: pd.Series) -> pd.Series:
    cleaned = (
        s.astype(str)
        .str.strip()
        .str.replace(r"[$,\s]", "", regex=True)
        .str.replace("%", "", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def validate(df: pd.DataFrame) -> ValidationReport:
    rep = ValidationReport()
    n = len(df)
    if n == 0:
        rep.stats = {
            "total_rows": 0,
            "valid_rows": 0,
            "rejected_rows": 0,
            "duplicate_rows": 0,
            "errors": 0,
            "warnings": 0,
        }
        return rep

    def add(idx, severity, rule, column, message):
        rep.issues.append(
            {
                "row_num": int(df.loc[idx, "_row_num"]),
                "severity": severity,
                "rule": rule,
                "column": column,
                "message": message,
            }
        )
        if severity == "error":
            rep.error_idx.add(idx)

    cols = df.columns
    has = lambda c: c in cols  # noqa: E731

    # ---- missing values by column (mapped canonical columns only) ----
    missing_by_col = {c: int(df[c].apply(_is_blank).sum()) for c in cols if not c.startswith("_")}

    # ---- order_id ----
    if has("order_id"):
        for idx in df[df["order_id"].apply(_is_blank)].index:
            add(idx, "error", "blank_order_id", "order_id", "Order ID is blank")

    # ---- order_date ----
    parsed_dates = None
    if has("order_date"):
        parsed_dates = pd.to_datetime(df["order_date"].astype(str).str.strip(), errors="coerce")
        upper = date.today() + timedelta(days=365)
        for idx in df.index:
            raw = str(df.loc[idx, "order_date"]).strip()
            if raw == "":
                add(idx, "error", "blank_date", "order_date", "Order date is blank")
            elif pd.isna(parsed_dates.loc[idx]):
                add(idx, "error", "invalid_date", "order_date", f"Unparseable date '{raw}'")
            else:
                d = parsed_dates.loc[idx].date()
                if d < DATE_MIN or d > upper:
                    add(
                        idx,
                        "error",
                        "date_out_of_bounds",
                        "order_date",
                        f"Date {d.isoformat()} outside {DATE_MIN.isoformat()}..{upper.isoformat()}",
                    )
    else:
        parsed_dates = pd.Series(pd.NaT, index=df.index)

    # ---- quantity ----
    qty = _num(df["quantity"]) if has("quantity") else pd.Series(float("nan"), index=df.index)
    if has("quantity"):
        for idx in df.index:
            raw = str(df.loc[idx, "quantity"]).strip()
            q = qty.loc[idx]
            if raw == "" or pd.isna(q):
                add(
                    idx,
                    "error",
                    "invalid_quantity",
                    "quantity",
                    f"Quantity '{raw}' is not a number",
                )
            elif q <= 0:
                add(
                    idx,
                    "error",
                    "nonpositive_quantity",
                    "quantity",
                    f"Quantity must be > 0 (got {q:g})",
                )

    # ---- money fields ----
    revenue = _num(df["revenue"]) if has("revenue") else pd.Series(float("nan"), index=df.index)
    unit_price = (
        _num(df["unit_price"]) if has("unit_price") else pd.Series(float("nan"), index=df.index)
    )
    cost = _num(df["cost"]) if has("cost") else pd.Series(0.0, index=df.index).fillna(0.0)
    shipping = (
        _num(df["shipping_cost"])
        if has("shipping_cost")
        else pd.Series(0.0, index=df.index).fillna(0.0)
    )
    cost = cost.fillna(0.0)
    shipping = shipping.fillna(0.0)

    for idx in df.index:
        if has("revenue") and not _is_blank(df.loc[idx, "revenue"]):
            r = revenue.loc[idx]
            if pd.isna(r):
                add(
                    idx,
                    "error",
                    "invalid_revenue",
                    "revenue",
                    f"Revenue '{df.loc[idx, 'revenue']}' is not a number",
                )
            elif r < 0:
                add(idx, "error", "negative_revenue", "revenue", f"Revenue is negative ({r:g})")
        if has("unit_price") and not _is_blank(df.loc[idx, "unit_price"]):
            p = unit_price.loc[idx]
            if pd.isna(p):
                add(
                    idx,
                    "error",
                    "invalid_price",
                    "unit_price",
                    f"Unit price '{df.loc[idx, 'unit_price']}' is not a number",
                )
            elif p < 0:
                add(idx, "error", "negative_price", "unit_price", f"Unit price is negative ({p:g})")
        if (
            has("cost")
            and not _is_blank(df.loc[idx, "cost"])
            and (pd.isna(cost.loc[idx]) or cost.loc[idx] < 0)
        ):
            add(idx, "error", "negative_cost", "cost", "Cost must be a number >= 0")
        if (
            has("shipping_cost")
            and not _is_blank(df.loc[idx, "shipping_cost"])
            and (pd.isna(shipping.loc[idx]) or shipping.loc[idx] < 0)
        ):
            add(idx, "error", "negative_shipping", "shipping_cost", "Shipping cost must be >= 0")

    # revenue derivability
    if has("revenue"):
        no_rev = revenue.isna()
        no_price = unit_price.isna()
        for idx in df[no_rev & no_price].index:
            if idx not in rep.error_idx or True:
                # only an error if quantity itself is usable; else quantity error already covers it
                if not pd.isna(qty.loc[idx]) and qty.loc[idx] > 0:
                    add(
                        idx,
                        "error",
                        "insufficient_revenue_fields",
                        "revenue",
                        "Revenue and unit price both missing; cannot derive revenue",
                    )

    # ---- discount ----
    disc_raw = df["discount"] if has("discount") else pd.Series("0", index=df.index)
    disc = _num(disc_raw)
    bad_disc = disc[~disc.isna() & ((disc < 0) | (disc > 100))]
    for idx in bad_disc.index:
        add(
            idx,
            "error",
            "discount_out_of_range",
            "discount",
            f"Discount must be between 0 and 100% (got {disc_raw.loc[idx]})",
        )

    # ---- profit consistency (warning; cleaner recomputes) ----
    if has("profit"):
        profit = _num(df["profit"])
        for idx in df.index:
            if idx in rep.error_idx:
                continue
            r, c, q, s, p = (
                revenue.loc[idx],
                cost.loc[idx],
                qty.loc[idx],
                shipping.loc[idx],
                profit.loc[idx],
            )
            if any(pd.isna(v) for v in [r, c, q, s, p]):
                continue
            expected = r - c * q - s
            if abs(p - expected) > max(0.05, 0.01 * abs(r)):
                add(
                    idx,
                    "warning",
                    "profit_mismatch",
                    "profit",
                    f"Profit {p:g} inconsistent with revenue-cost-qty-shipping ({expected:,.2f}); will recompute",
                )

    # ---- duplicates ----
    key_cols = [c for c in df.columns if not c.startswith("_")]
    dup_mask = df.duplicated(subset=key_cols, keep="first")
    for idx in df[dup_mask].index:
        if idx not in rep.error_idx:
            rep.dupe_idx.add(idx)
    if has("order_id"):
        for oid, grp in df[~dup_mask].groupby("order_id", dropna=False):
            if str(oid).strip() == "" or len(grp) < 2:
                continue
            # same order_id, different content -> needs attention but stays valid
            for idx in grp.index[1:]:
                rep.issues.append(
                    {
                        "row_num": int(df.loc[idx, "_row_num"]),
                        "severity": "warning",
                        "rule": "duplicate_order_id",
                        "column": "order_id",
                        "message": f"Order ID '{oid}' appears {len(grp)}x with different content",
                    }
                )

    # ---- warnings: missing links, unknown vocab, outliers ----
    if has("customer_id"):
        for idx in df[df["customer_id"].apply(_is_blank)].index:
            rep.issues.append(
                {
                    "row_num": int(df.loc[idx, "_row_num"]),
                    "severity": "warning",
                    "rule": "missing_customer_id",
                    "column": "customer_id",
                    "message": "Customer ID is blank",
                }
            )
    if has("product_id"):
        for idx in df[df["product_id"].apply(_is_blank)].index:
            rep.issues.append(
                {
                    "row_num": int(df.loc[idx, "_row_num"]),
                    "severity": "warning",
                    "rule": "missing_product_id",
                    "column": "product_id",
                    "message": "Product ID is blank",
                }
            )
    if has("category"):
        for idx in df.index:
            v = str(df.loc[idx, "category"]).strip()
            if v and v.lower() not in CATEGORY_MAP:
                rep.issues.append(
                    {
                        "row_num": int(df.loc[idx, "_row_num"]),
                        "severity": "warning",
                        "rule": "unknown_category",
                        "column": "category",
                        "message": f"Unknown category '{v}'",
                    }
                )
    if has("region"):
        for idx in df.index:
            v = str(df.loc[idx, "region"]).strip()
            if (
                v
                and v.lower() not in REGION_MAP
                and v.lower() not in {r.lower() for r in REGION_MAP.values()}
            ):
                rep.issues.append(
                    {
                        "row_num": int(df.loc[idx, "_row_num"]),
                        "severity": "warning",
                        "rule": "unknown_region",
                        "column": "region",
                        "message": f"Unknown region '{v}'",
                    }
                )
    if has("order_status"):
        for idx in df.index:
            v = str(df.loc[idx, "order_status"]).strip()
            if v and v.lower() not in STATUS_MAP:
                rep.issues.append(
                    {
                        "row_num": int(df.loc[idx, "_row_num"]),
                        "severity": "warning",
                        "rule": "invalid_status",
                        "column": "order_status",
                        "message": f"Unknown order status '{v}'",
                    }
                )

    # outliers (|z| > 3) on otherwise-valid rows
    valid_for_stats = [i for i in df.index if i not in rep.error_idx and i not in rep.dupe_idx]
    outlier_qty, outlier_rev = 0, 0
    for series, name in ((qty, "quantity"), (revenue, "revenue")):
        vals = series.loc[valid_for_stats].dropna()
        if len(vals) >= 10 and vals.std(ddof=0) > 0:
            z = (vals - vals.mean()) / vals.std(ddof=0)
            for idx in vals[abs(z) > 3].index:
                rep.issues.append(
                    {
                        "row_num": int(df.loc[idx, "_row_num"]),
                        "severity": "warning",
                        "rule": f"outlier_{name}",
                        "column": name,
                        "message": f"Outlier {name}={vals.loc[idx]:g} (|z|>3)",
                    }
                )
                if name == "quantity":
                    outlier_qty += 1
                else:
                    outlier_rev += 1

    invalid_by_col: dict[str, int] = {}
    for iss in rep.issues:
        if iss["severity"] == "error":
            invalid_by_col[iss["column"]] = invalid_by_col.get(iss["column"], 0) + 1

    rejected = len(rep.error_idx)
    dupes = len(rep.dupe_idx)
    rep.stats = {
        "total_rows": n,
        "rejected_rows": rejected,
        "duplicate_rows": dupes,
        "valid_rows": n - rejected - dupes,
        "errors": sum(1 for i in rep.issues if i["severity"] == "error"),
        "warnings": sum(1 for i in rep.issues if i["severity"] == "warning"),
        "missing_by_column": missing_by_col,
        "invalid_by_column": invalid_by_col,
        "outlier_quantity": outlier_qty,
        "outlier_revenue": outlier_rev,
    }
    return rep
