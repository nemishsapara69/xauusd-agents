import numpy as np
import pandas as pd
import pytest

from core.indicators import add_emas, atr, ema


def test_ema_matches_recursive_calculation() -> None:
    values = pd.Series([10.0, 11.0, 13.0, 12.0, 14.0])
    expected = values.ewm(span=3, adjust=False, min_periods=3).mean()
    pd.testing.assert_series_equal(ema(values, 3), expected)


def test_atr_uses_wilder_smoothing() -> None:
    frame = pd.DataFrame(
        {
            "high": [10, 12, 13, 15, 14],
            "low": [8, 9, 10, 11, 12],
            "close": [9, 11, 12, 13, 13],
        },
        dtype=float,
    )
    result = atr(frame, 3)
    true_range = pd.Series([2.0, 3.0, 3.0, 4.0, 2.0])
    expected = true_range.ewm(alpha=1 / 3, adjust=False, min_periods=3).mean()
    pd.testing.assert_series_equal(result, expected)


def test_add_emas_does_not_mutate_input() -> None:
    frame = pd.DataFrame({"close": np.arange(1.0, 205.0), "high": 205.0, "low": 0.0})
    result = add_emas(frame)
    assert "ema_20" not in frame
    assert {"ema_20", "ema_50", "ema_200", "atr_14"} <= set(result.columns)
    assert result["ema_200"].iloc[-1] == pytest.approx(
        frame["close"].ewm(span=200, adjust=False, min_periods=200).mean().iloc[-1]
    )