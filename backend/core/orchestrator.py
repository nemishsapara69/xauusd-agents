from __future__ import annotations

from typing import Any, Awaitable, Callable

import pandas as pd

from agents.analysis_agent import analyze
from agents.level_agent import find_signal
from agents.news_agent import NewsAgent
from agents.reporting_agent import ReportingAgent
from agents.risk_execution_agent import RiskExecutionAgent
from core.event_bus import EventBus
from database.db import Database
from api.control import trading_allowed
from core.config import load_config
from core.mt5_client import MT5Client
from agents.risk_execution_agent import RiskLimits


class Orchestrator:
    def __init__(self, event_bus: EventBus, database: Database | None = None) -> None:
        self.bus = event_bus
        self.database = database or Database()
        self.news = NewsAgent()
        rules = load_config().risk_rules
        self.risk = RiskExecutionAgent(RiskLimits(
            risk_per_trade_usd=float(rules.get("risk_per_trade_usd", 50)),
            max_daily_loss_usd=float(rules.get("max_daily_loss_usd", 1000)),
            max_open_positions=int(rules.get("max_open_positions", 10)),
            max_spread_points=float(rules.get("max_spread_points", 50)),
            min_risk_reward=float(rules.get("min_risk_reward", 2.0)),
            stop_loss_pips=float(rules.get("stop_loss_pips", 50.0)),
            max_take_profit_pips=float(rules.get("max_take_profit_pips", 100.0)),
            pip_size=float(rules.get("pip_size", 0.01)),
        ))
        self.reporting = ReportingAgent(self.database)

    async def run(
        self,
        frames: dict[str, pd.DataFrame],
        symbol: str,
        *,
        daily_loss_usd: float = 0.0,
        open_positions: int = 0,
    ) -> dict[str, Any]:
        news = self.news.check()
        await self.bus.publish({"type": "agent_step", "agent": "news", "payload": news})
        trend = analyze(frames["M15"], frames["H1"])
        await self.bus.publish({"type": "agent_step", "agent": "analysis", "payload": trend})
        signal = find_signal(
            frames["M15"],
            trend["trend"],
            symbol,
            risk_reward=self.risk.limits.min_risk_reward,
            stop_loss_pips=self.risk.limits.stop_loss_pips,
            max_take_profit_pips=self.risk.limits.max_take_profit_pips,
            pip_size=self.risk.limits.pip_size,
        )
        signal_payload = signal or {"status": "no_signal"}
        self.database.add_event("level", "signal", signal_payload)
        await self.bus.publish({"type": "agent_step", "agent": "level", "payload": signal_payload})
        if not trading_allowed():
            decision = {"approved": False, "reason": "kill_switch_or_stopped"}
        elif not signal or not news["trade_allowed"]:
            decision = {"approved": False, "reason": "news_filter" if not news["trade_allowed"] else "no_signal"}
        else:
            decision = self.risk.check_signal(
                signal,
                daily_loss_usd=daily_loss_usd,
                open_positions=open_positions,
            )
        await self.bus.publish({"type": "agent_step", "agent": "risk", "payload": decision})
        if signal and decision["approved"]:
            if load_config().execution_enabled:
                config = load_config()
                client = MT5Client(config)
                try:
                    client.connect()
                    current_positions = client.get_positions(signal["symbol"])
                    if len(current_positions) >= min(self.risk.limits.max_open_positions, 10):
                        decision = {"approved": False, "reason": "max_open_positions"}
                        result = {"status": "not_executed"}
                    else:
                        result = {
                            "status": "executed",
                            "result": client.place_market_order(signal, float(decision["lot_size"])),
                        }
                finally:
                    client.close()
            else:
                result = self.risk.place_order(signal, decision)
            self.reporting.record(signal, {**decision, **result}, {})
        else:
            result = {"status": "not_executed"}
        await self.bus.publish({"type": "agent_step", "agent": "reporting", "payload": result})
        return {"news": news, "trend": trend, "signal": signal, "decision": decision, "result": result}