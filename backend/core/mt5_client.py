"""Read-only MetaTrader 5 client."""

from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Any

import pandas as pd

from .config import AppConfig, ConfigurationError, load_config

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


class MT5ClientError(RuntimeError):
    """Raised when an MT5 read operation fails."""


class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


def _timeframe_value(timeframe: str | Timeframe) -> Any:
    if mt5 is None:
        raise MT5ClientError("MetaTrader5 package is not installed")
    name = timeframe.value if isinstance(timeframe, Timeframe) else str(timeframe).upper()
    try:
        return getattr(mt5, f"TIMEFRAME_{name}")
    except AttributeError as exc:
        raise ValueError(f"Unsupported MT5 timeframe: {name}") from exc


class MT5Client:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        self._connected = False

    def connect(self) -> None:
        if mt5 is None:
            raise MT5ClientError("MetaTrader5 package is not installed")
        if not self.config.mt5_path.exists():
            raise ConfigurationError(f"MT5 terminal not found: {self.config.mt5_path}")
        if not mt5.initialize(
            path=str(self.config.mt5_path),
            login=self.config.mt5_login,
            password=self.config.mt5_password,
            server=self.config.mt5_server,
        ):
            raise MT5ClientError(f"MT5 initialization failed: {mt5.last_error()}")
        self._connected = True

    def close(self) -> None:
        # MT5 uses one process-wide IPC connection. Request-scoped clients
        # must not shut it down while the live market-data task is using it.
        self._connected = False

    @staticmethod
    def shutdown() -> None:
        if mt5 is not None:
            mt5.shutdown()

    def _require_connection(self) -> None:
        if not self._connected:
            raise MT5ClientError("MT5 client is not connected")

    def get_candles(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        count: int,
        include_current: bool = False,
    ) -> pd.DataFrame:
        self._require_connection()
        if count <= 0:
            raise ValueError("count must be positive")
        rates = mt5.copy_rates_from_pos(
            symbol, _timeframe_value(timeframe), 0 if include_current else 1, count
        )
        if rates is None:
            raise MT5ClientError(f"Unable to retrieve candles for {symbol}: {mt5.last_error()}")
        candles = pd.DataFrame(rates)
        if candles.empty:
            raise MT5ClientError(f"No candles returned for {symbol}")
        candles["time"] = pd.to_datetime(candles["time"], unit="s", utc=True)
        return candles.sort_values("time").reset_index(drop=True)

    def get_account(self) -> Any:
        self._require_connection()
        account = mt5.account_info()
        if account is None:
            raise MT5ClientError(f"Unable to retrieve account information: {mt5.last_error()}")
        return account._asdict() if hasattr(account, "_asdict") else account

    def get_tick(self, symbol: str) -> Any:
        self._require_connection()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5ClientError(f"Unable to retrieve tick for {symbol}: {mt5.last_error()}")
        return tick._asdict() if hasattr(tick, "_asdict") else tick

    def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        self._require_connection()
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            raise MT5ClientError(f"Unable to retrieve positions: {mt5.last_error()}")
        return [position._asdict() if hasattr(position, "_asdict") else position for position in positions]

    def get_deals(self, date_from: datetime, date_to: datetime, symbol: str | None = None) -> list[dict[str, Any]]:
        self._require_connection()
        deals = mt5.history_deals_get(date_from, date_to, symbol=symbol) if symbol else mt5.history_deals_get(date_from, date_to)
        if deals is None:
            raise MT5ClientError(f"Unable to retrieve deal history: {mt5.last_error()}")
        return [deal._asdict() if hasattr(deal, "_asdict") else deal for deal in deals]

    def place_market_order(self, signal: dict[str, Any], volume: float) -> dict[str, Any]:
        """Send one protected market order for an approved signal."""
        self._require_connection()
        if volume <= 0:
            raise ValueError("Order volume must be positive")
        symbol = str(signal["symbol"])
        if not mt5.symbol_select(symbol, True):
            raise MT5ClientError(f"Unable to select symbol {symbol}: {mt5.last_error()}")
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if tick is None or info is None:
            raise MT5ClientError(f"Unable to read trading symbol {symbol}: {mt5.last_error()}")
        side = str(signal["side"]).lower()
        order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
        price = float(tick.ask if side == "buy" else tick.bid)
        digits = int(info.digits)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": round(float(volume), 2),
            "type": order_type,
            "price": round(price, digits),
            "sl": round(float(signal["sl"]), digits),
            "tp": round(float(signal["tp"]), digits),
            "deviation": 20,
            "magic": 505789,
            "comment": "XAUUSD agents approved",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": getattr(mt5, "ORDER_FILLING_IOC", 1),
        }
        result = mt5.order_send(request)
        if result is None:
            raise MT5ClientError(f"MT5 order failed: {mt5.last_error()}")
        response = result._asdict() if hasattr(result, "_asdict") else result
        if response.get("retcode") != mt5.TRADE_RETCODE_DONE:
            raise MT5ClientError(f"MT5 order rejected: {response}")
        return response


if __name__ == "__main__":
    client = MT5Client()
    try:
        client.connect()
        print(client.get_candles(client.config.symbol, client.config.default_timeframe, 5).to_string(index=False))
        print(client.get_account())
        print(client.get_tick(client.config.symbol))
    finally:
        client.close()