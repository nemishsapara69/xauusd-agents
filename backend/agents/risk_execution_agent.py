"""Hard risk checks and dry-run execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
import logging
from typing import Any


@dataclass(frozen=True)
class RiskLimits:
    risk_per_trade_usd: float = 50.0
    max_daily_loss_usd: float = 1000.0
    max_open_positions: int = 10
    max_spread_points: float = 50.0
    min_risk_reward: float = 2.0
    stop_loss_pips: float = 50.0
    max_take_profit_pips: float = 100.0
    pip_size: float = 0.01
    session_start_utc: time = time(7, 0)
    session_end_utc: time = time(21, 0)


class RiskExecutionAgent:
    def __init__(self, limits: RiskLimits | None = None, logger: logging.Logger | None = None) -> None:
        self.limits = limits or RiskLimits()
        self.logger = logger or logging.getLogger("xauusd.risk")

    def check_signal(
        self,
        signal: dict[str, Any],
        *,
        daily_loss_usd: float = 0.0,
        open_positions: int = 0,
        spread_points: float = 0.0,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        required = ("side", "entry", "sl", "tp")
        if any(key not in signal or signal[key] is None for key in required):
            return {"approved": False, "reason": "invalid_signal"}
        entry, stop, target = float(signal["entry"]), float(signal["sl"]), float(signal["tp"])
        risk = abs(entry - stop)
        reward = abs(target - entry)
        max_reward = self.limits.max_take_profit_pips * self.limits.pip_size
        max_stop = self.limits.stop_loss_pips * self.limits.pip_size
        if daily_loss_usd >= self.limits.max_daily_loss_usd:
            return {"approved": False, "reason": "daily_loss_limit"}
        if open_positions >= self.limits.max_open_positions:
            return {"approved": False, "reason": "max_open_positions"}
        if spread_points > self.limits.max_spread_points:
            return {"approved": False, "reason": "spread_limit"}
        current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).time()
        if not self.limits.session_start_utc <= current_time <= self.limits.session_end_utc:
            return {"approved": False, "reason": "session_filter"}
        if (
            risk <= 0
            or self.limits.pip_size <= 0
            or self.limits.max_take_profit_pips <= 0
            or self.limits.stop_loss_pips <= 0
            or risk > max_stop + 1e-9
            or reward > max_reward + 1e-9
            or reward / risk < self.limits.min_risk_reward
        ):
            return {"approved": False, "reason": "minimum_risk_reward"}
        lot_size = self.calc_lot_size(self.limits.risk_per_trade_usd, risk)
        return {"approved": True, "reason": "approved", "risk_amount": self.limits.risk_per_trade_usd, "lot_size": lot_size}

    @staticmethod
    def calc_lot_size(risk_amount_usd: float, stop_distance: float, value_per_price_unit: float = 100.0) -> float:
        if risk_amount_usd <= 0 or stop_distance <= 0 or value_per_price_unit <= 0:
            raise ValueError("risk amount, stop distance, and value per price unit must be positive")
        return round(risk_amount_usd / (stop_distance * value_per_price_unit), 2)

    def place_order(self, signal: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        if not decision.get("approved"):
            raise ValueError("cannot dry-run a rejected signal")
        result = {"status": "dry_run", "message": "would place order", "signal": signal, "decision": decision}
        self.logger.info("DRY RUN: would place %s", result)
        return result


def manage_trade(
    trade: dict[str, Any],
    price: float,
    ema20: float,
) -> dict[str, Any]:
    """Apply break-even at 1R, partial at 1.5R, and EMA20 trailing."""
    entry = float(trade["entry"])
    initial_sl = float(trade["initial_sl"])
    side = trade["side"]
    risk = abs(entry - initial_sl)
    move = price - entry if side == "buy" else entry - price
    result = dict(trade)
    result.setdefault("partial_closed", False)
    result.setdefault("break_even", False)
    if move >= risk:
        result["stop_loss"] = entry
        result["break_even"] = True
    if move >= 1.5 * risk:
        result["partial_closed"] = True
    if move >= risk:
        result["stop_loss"] = max(float(result["stop_loss"]), ema20) if side == "buy" else min(float(result["stop_loss"]), ema20)
    return result