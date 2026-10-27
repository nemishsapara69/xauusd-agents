"""EMA trend analysis for the M15 and H1 timeframes."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from core.indicators import add_emas


def _timeframe_trend(frame: pd.DataFrame) -> dict[str, Any]:
    enriched = add_emas(frame)
    if len(enriched) < 2:
        return {"trend": "no_trade", "strength": "weak", "alignment": ""}
    row = enriched.iloc[-1]
    previous = enriched.iloc[-2]
    bullish = (
        row["ema_20"] > row["ema_50"] > row["ema_200"]
        and row["close"] > row["ema_50"]
        and row["ema_50"] > previous["ema_50"]
    )
    bearish = (
        row["ema_20"] < row["ema_50"] < row["ema_200"]
        and row["close"] < row["ema_50"]
        and row["ema_50"] < previous["ema_50"]
    )
    if bullish:
        return {"trend": "bullish", "strength": "strong"}
    if bearish:
        return {"trend": "bearish", "strength": "strong"}
    return {"trend": "no_trade", "strength": "weak"}


def analyze(m15: pd.DataFrame, h1: pd.DataFrame) -> dict[str, Any]:
    """Return a tradeable trend only when M15 and H1 agree."""
    m15_result = _timeframe_trend(m15)
    h1_result = _timeframe_trend(h1)
    aligned = m15_result["trend"] in {"bullish", "bearish"} and m15_result["trend"] == h1_result["trend"]
    return {
        "trend": m15_result["trend"] if aligned else "no_trade",
        "strength": "strong" if aligned else "weak",
        "alignment": "M15+H1" if aligned else "",
        "m15": m15_result["trend"],
        "h1": h1_result["trend"],
    }


def analyze_dates(m15: pd.DataFrame, h1: pd.DataFrame, dates: int = 20) -> list[dict[str, Any]]:
    """Evaluate the last ``dates`` M15 closes for historical inspection."""
    if dates <= 0:
        raise ValueError("dates must be positive")
    results = []
    for end in range(max(2, len(m15) - dates), len(m15) + 1):
        m15_slice = m15.iloc[:end]
        h1_slice = h1[h1["time"] <= m15_slice.iloc[-1]["time"]] if "time" in h1 else h1
        if len(h1_slice) >= 2:
            results.append(analyze(m15_slice, h1_slice))
    return results