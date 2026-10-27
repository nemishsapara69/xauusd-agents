from __future__ import annotations

from typing import Any

from database.db import Database


class ReportingAgent:
    def __init__(self, database: Database | None = None) -> None:
        self.database = database or Database()

    def record(self, signal: dict[str, Any], decision: dict[str, Any], ema_state: dict[str, Any] | None = None) -> int:
        return self.database.add_trade(signal, decision, ema_state)

    def report(self, period: str = "daily") -> dict[str, Any]:
        trades = self.database.rows("trades", 10000)
        summary = self.database.summary()
        pnl_values = [float(item.get("pnl", 0) or 0) for item in trades]
        running = peak = drawdown = 0.0
        for value in reversed(pnl_values):
            running += value
            peak = max(peak, running)
            drawdown = max(drawdown, peak - running)
        summary.update({
            "period": period,
            "drawdown": drawdown,
            "best_trade": max(pnl_values, default=0),
            "worst_trade": min(pnl_values, default=0),
            "insight": "Review EMA pullback performance as the trade sample grows.",
        })
        return summary