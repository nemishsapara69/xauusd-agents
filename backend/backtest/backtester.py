"""Deterministic, signal-only backtester for the Phase 3 strategy."""

from __future__ import annotations

from typing import Any

import pandas as pd

from agents.analysis_agent import analyze
from agents.level_agent import find_signal
from agents.risk_execution_agent import RiskExecutionAgent
from core.indicators import add_emas


def run_backtest(
    m15: pd.DataFrame,
    h1: pd.DataFrame,
    h4: pd.DataFrame,
    starting_balance: float = 10_000,
) -> dict[str, Any]:
    if starting_balance <= 0:
        raise ValueError("starting_balance must be positive")
    m15 = add_emas(m15)
    h1 = add_emas(h1)
    h4 = add_emas(h4)
    risk = RiskExecutionAgent()
    balance = starting_balance
    equity_curve = [{"time": str(m15.iloc[0]["time"]), "equity": balance}] if len(m15) else []
    trades = []
    for index in range(200, len(m15)):
        history = m15.iloc[:index]
        trend = analyze(
            m15.iloc[:index],
            h1[h1["time"] <= m15.iloc[index]["time"]],
        )
        signal = find_signal(history, trend["trend"])
        if not signal:
            equity_curve.append({"time": str(m15.iloc[index]["time"]), "equity": balance})
            continue
        decision = risk.check_signal(signal, now=m15.iloc[index]["time"].to_pydatetime())
        if not decision["approved"]:
            continue
        future = m15.iloc[index : index + 20]
        outcome = 0.0
        for _, candle in future.iterrows():
            if signal["side"] == "buy":
                if candle["low"] <= signal["sl"]:
                    outcome = -1.0
                    break
                if candle["high"] >= signal["tp"]:
                    outcome = 2.0
                    break
            else:
                if candle["high"] >= signal["sl"]:
                    outcome = -1.0
                    break
                if candle["low"] <= signal["tp"]:
                    outcome = 2.0
                    break
        pnl = decision["risk_amount"] * outcome
        balance += pnl
        trades.append({"time": str(m15.iloc[index]["time"]), "pnl": pnl, "outcome_r": outcome})
        equity_curve.append({"time": str(m15.iloc[index]["time"]), "equity": balance})
    pnls = [trade["pnl"] for trade in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    gross_loss = abs(sum(losses))
    peak = starting_balance
    max_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point["equity"])
        max_drawdown = max(max_drawdown, peak - point["equity"])
    return {
        "starting_balance": starting_balance,
        "ending_balance": balance,
        "trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "profit_factor": sum(wins) / gross_loss if gross_loss else (float("inf") if wins else 0),
        "max_drawdown": max_drawdown,
        "trades_detail": trades,
        "equity_curve": equity_curve,
    }