"""Part 5: target tracking math (variance + run-rate)."""

from app.analytics.kpi_catalog import growth


def test_variance_and_progress():
    assert growth(90, 100) == -10.0
    assert growth(100, 0) is None
    # required daily = (target - actual) / remaining
    assert (100000 - 60000) / 10 == 4000.0
