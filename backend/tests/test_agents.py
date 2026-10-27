from datetime import datetime, timezone

import pandas as pd

from agents.analysis_agent import analyze
from agents.news_agent import NewsAgent, NewsEvent
from agents.risk_execution_agent import RiskExecutionAgent
from agents.risk_execution_agent import manage_trade


def _trend_frame(direction: str) -> pd.DataFrame:
    close = [100 + index * (1 if direction == "bullish" else -1) for index in range(260)]
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=len(close), freq="h", tz="UTC"),
            "open": close,
            "high": [value + 1 for value in close],
            "low": [value - 1 for value in close],
            "close": close,
        }
    )


def test_analysis_requires_m15_and_h1_alignment() -> None:
    result = analyze(_trend_frame("bullish"), _trend_frame("bullish"))
    assert result["trend"] == "bullish"
    assert result["alignment"] == "M15+H1"
    assert analyze(_trend_frame("bullish"), _trend_frame("bearish"))["trend"] == "no_trade"


def test_news_blocks_thirty_minutes_around_high_impact_event() -> None:
    event_time = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    agent = NewsAgent(
        fetcher=lambda: [NewsEvent(event_time, "USD", "high", "CPI")],
        summarizer=lambda event: "CPI summary",
    )
    assert agent.check(event_time)["trade_allowed"] is False
    assert agent.check(event_time + pd.Timedelta(minutes=31).to_pytimedelta())["trade_allowed"] is True


def test_risk_rejects_spread_and_daily_limit() -> None:
    agent = RiskExecutionAgent()
    signal = {"side": "buy", "entry": 2000, "sl": 1999.5, "tp": 2001}
    assert agent.check_signal(signal, spread_points=51, now=datetime(2026, 1, 1, 12, tzinfo=timezone.utc))["reason"] == "spread_limit"
    assert agent.check_signal(signal, daily_loss_usd=1000, now=datetime(2026, 1, 1, 12, tzinfo=timezone.utc))["reason"] == "daily_loss_limit"


def test_trade_management_moves_stop_and_partially_closes() -> None:
    trade = {"side": "buy", "entry": 2000, "initial_sl": 1990, "stop_loss": 1990}
    result = manage_trade(trade, 2015, 2008)
    assert result["break_even"] is True
    assert result["partial_closed"] is True
    assert result["stop_loss"] == 2008


def test_risk_limits_cap_target_distance_and_keep_two_to_one_ratio() -> None:
    agent = RiskExecutionAgent()
    decision = agent.check_signal(
        {"side": "buy", "entry": 2000, "sl": 1999.5, "tp": 2001},
        now=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
    )
    assert decision["approved"] is True


def test_risk_rejects_target_capped_below_minimum_ratio() -> None:
    agent = RiskExecutionAgent()
    decision = agent.check_signal(
        {"side": "buy", "entry": 2000, "sl": 1998.5, "tp": 2001},
        now=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
    )
    assert decision["approved"] is False
    assert decision["reason"] == "minimum_risk_reward"
