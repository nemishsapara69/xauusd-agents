"""Typed contracts shared by agents, APIs, and WebSocket events."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any


class Direction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TrendResult:
    symbol: str
    timeframe: str
    direction: Direction
    ema_fast: float
    ema_slow: float
    ema_long: float
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class TradeSignal:
    symbol: str
    direction: Direction
    action: str
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    reason: str = ""
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class RiskDecision:
    approved: bool
    reason: str
    risk_amount: float = 0.0
    lot_size: float = 0.0
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class TradeRecord:
    ticket: int | None
    symbol: str
    direction: Direction
    volume: float
    entry: float
    stop_loss: float | None = None
    take_profit: float | None = None
    status: str = "pending"
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class AgentStatus:
    name: str
    status: str
    message: str = ""
    last_update: datetime = field(default_factory=utc_now)


class _JSONEncoder(json.JSONEncoder):
    def default(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        return super().default(value)


def model_to_dict(model: Any) -> dict[str, Any]:
    return asdict(model)


def model_to_json(model: Any) -> str:
    return json.dumps(model_to_dict(model), cls=_JSONEncoder)