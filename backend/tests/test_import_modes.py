"""Part 2: import modes, quality filters, formula guard."""

import pandas as pd

from app.ingestion.cleaner import clean
from app.ingestion.validator import validate


def _frame(rows):
    df = pd.DataFrame(rows)
    df["_row_num"] = range(1, len(df) + 1)
    return df


def test_formula_cells_neutralized():
    df = _frame(
        [
            {
                "order_id": "=1+1",
                "order_date": "2024-01-02",
                "quantity": "1",
                "unit_price": "10",
                "revenue": "10",
                "customer_name": "@bad",
            }
        ]
    )
    rep = validate(df)
    out = clean(df, rep)
    assert out.cleaned.loc[0, "order_id"] == "'=1+1"
    assert out.cleaned.loc[0, "customer_name"] == "'@bad"
    assert any(t["step"] == "neutralize_formulas" for t in out.transformations)


def test_quality_stats_overlap_documented():
    # duplicate + invalid date overlap: issue counts are not mutually exclusive
    df = _frame(
        [
            {
                "order_id": "A",
                "order_date": "bad-date",
                "quantity": "1",
                "unit_price": "10",
                "revenue": "10",
            },
            {
                "order_id": "A",
                "order_date": "bad-date",
                "quantity": "1",
                "unit_price": "10",
                "revenue": "10",
            },
        ]
    )
    rep = validate(df)
    assert rep.stats["total_rows"] == 2
    # both rows invalid; counts may overlap by design
    assert rep.stats["rejected_rows"] == 2
