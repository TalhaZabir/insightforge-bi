"""Unit tests for centralized KPI catalog — edge cases."""

from app.analytics import kpi_catalog as K


def test_margin_zero_revenue_returns_none():
    assert K.margin(10, 0) is None
    assert K.margin_or_zero(10, 0) == 0.0
    assert K.margin(50, 100) == 0.5


def test_aov_zero_orders():
    assert K.aov(100, 0) is None
    assert K.aov_or_zero(100, 0) == 0.0
    assert K.aov(300, 3) == 100.0


def test_growth_edge_cases():
    assert K.growth(100, None) is None
    assert K.growth(100, 0) is None
    assert K.growth(120, 100) == 20.0
    # negative baseline uses abs()
    assert K.growth(-50, -100) == 50.0
    assert K.growth(0, 100) == -100.0


def test_margin_delta():
    import pytest as _pytest

    assert K.margin_delta_pp(0.3, 0.2) == _pytest.approx(10.0)
    assert K.margin_delta_pp(None, 0.2) is None


def test_repeat_rate_empty():
    assert K.repeat_rate(0, 0) == 0.0
    assert K.repeat_rate(1, 4) == 25.0


def test_low_margin_flag():
    assert K.is_low_margin(0.05, 100) is True
    assert K.is_low_margin(0.15, 100) is False
    assert K.is_low_margin(0.05, 0) is False


def test_pack_row_consistency():
    r = K.pack_kpi_row(335.0, 120.0, 3, 5.0)
    assert r["margin"] == 120.0 / 335.0
    assert r["aov"] == 335.0 / 3
    e = K.pack_kpi_row(0.0, 0.0, 0, 0.0)
    assert e["margin"] == 0.0 and e["aov"] == 0.0
    assert e["margin_or_none"] is None and e["aov_or_none"] is None


def test_decimal_input():
    from decimal import Decimal

    assert K.to_float(Decimal("10.5")) == 10.5
    assert K.to_float(None) == 0.0
