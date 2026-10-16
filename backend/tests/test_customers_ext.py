"""Part 3: RFM + cohort unit tests on synthetic per-customer aggregates."""

from app.analytics.customers_ext import _label, _quintile_scores


def test_quintile_rank_based():
    s = _quintile_scores([10, 20, 30, 40, 50], higher_better=True)
    assert s[4] == 5 and s[0] == 1
    assert sorted(s) == [1, 2, 3, 4, 5]


def test_quintile_ties_deterministic():
    s1 = _quintile_scores([5, 5, 5], higher_better=True)
    s2 = _quintile_scores([5, 5, 5], higher_better=True)
    assert s1 == s2 and all(1 <= v <= 5 for v in s1)


def test_labels():
    assert _label(15) == "Champions"
    assert _label(11) == "Loyal"
    assert _label(8) == "Potential"
    assert _label(5) == "At-risk"
    assert _label(3) == "Hibernating"
