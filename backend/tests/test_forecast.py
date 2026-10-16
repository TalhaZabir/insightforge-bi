"""Part 4: forecasting accuracy math."""

from app.analytics.forecast import _mae, _rmse, _wape


def test_metrics():
    assert _mae([100, 200], [110, 190]) == 10.0
    assert _rmse([100, 200], [100, 200]) == 0.0
    assert _wape([100, 200], [110, 190]) is not None
    assert _wape([0, 0], [1, 1]) is None
    assert _mae([], []) is None
