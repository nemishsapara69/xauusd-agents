"""Technical indicators used by the strategy."""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    if not isinstance(series, pd.Series):
        raise TypeError("series must be a pandas Series")
    return series.astype(float).ewm(span=period, adjust=False, min_periods=period).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    required = {"high", "low", "close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing OHLC columns: {', '.join(sorted(missing))}")
    previous_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def add_emas(df: pd.DataFrame, periods: tuple[int, ...] = (20, 50, 200)) -> pd.DataFrame:
    result = df.copy()
    for period in periods:
        result[f"ema_{period}"] = ema(result["close"], period)
    result["atr_14"] = atr(result, 14)
    return result