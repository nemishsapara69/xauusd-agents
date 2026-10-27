"""M15 EMA retest and confirmation signal detection."""

from __future__ import annotations

from typing import Any

import pandas as pd

from core.indicators import add_emas


def _swing_stop(frame: pd.DataFrame, bullish: bool, entry: float, atr_value: float) -> float:
    window = frame.tail(5)
    if bullish:
        swing = float(window["low"].min())
        return min(swing, entry - atr_value) if swing < entry else entry - atr_value
    swing = float(window["high"].max())
    return max(swing, entry + atr_value) if swing > entry else entry + atr_value


def find_signal(
    frame: pd.DataFrame,
    trend: str,
    symbol: str = "XAUUSD",
    *,
    risk_reward: float = 2.0,
    stop_loss_pips: float = 50.0,
    max_take_profit_pips: float = 100.0,
    pip_size: float = 0.01,
) -> dict[str, Any] | None:
    """Find the most recent confirmed EMA retest in the supplied closed candles."""
    if trend not in {"bullish", "bearish"}:
        return None
    data = add_emas(frame)
    if len(data) < 25:
        return None
    previous = data.iloc[-2]
    current = data.iloc[-1]
    bullish = trend == "bullish"
    touched = (
        min(previous["open"], previous["close"]) <= previous["ema_20"] <= max(previous["open"], previous["close"])
        or previous["low"] <= previous["ema_50"] <= previous["high"]
    )
    confirmation = current["close"] > current["open"] if bullish else current["close"] < current["open"]
    if not touched or not confirmation:
        return None
    entry = float(current["close"])
    atr_value = float(current["atr_14"])
    if stop_loss_pips <= 0 or pip_size <= 0:
        return None
    stop_distance = stop_loss_pips * pip_size
    stop_loss = entry - stop_distance if bullish else entry + stop_distance
    risk = abs(entry - stop_loss)
    if risk <= 0:
        return None
    if risk_reward <= 0 or max_take_profit_pips <= 0 or pip_size <= 0:
        return None
    target_distance = min(risk * risk_reward, max_take_profit_pips * pip_size)
    target = entry + target_distance if bullish else entry - target_distance
    return {
        "symbol": symbol,
        "side": "buy" if bullish else "sell",
        "entry": entry,
        "sl": stop_loss,
        "tp": target,
        "risk_reward": target_distance / risk,
        "take_profit_pips": target_distance / pip_size,
        "time": current["time"].isoformat() if hasattr(current["time"], "isoformat") else current["time"],
    }