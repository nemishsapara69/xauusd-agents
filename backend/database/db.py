from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "xauusd.sqlite3"


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL,
                    side TEXT NOT NULL, entry REAL NOT NULL, stop_loss REAL,
                    take_profit REAL, volume REAL NOT NULL, status TEXT NOT NULL,
                    pnl REAL DEFAULT 0, reason TEXT, ema_state TEXT,
                    created_at TEXT NOT NULL, closed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL,
                    side TEXT, entry REAL, stop_loss REAL, take_profit REAL,
                    risk_reward REAL, reason TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL,
                    event_type TEXT NOT NULL, payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY, pnl REAL NOT NULL DEFAULT 0,
                    trades INTEGER NOT NULL DEFAULT 0, wins INTEGER NOT NULL DEFAULT 0,
                    drawdown REAL NOT NULL DEFAULT 0
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_event(self, agent: str, event_type: str, payload: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO agent_events(agent,event_type,payload,created_at) VALUES(?,?,?,?)",
                (agent, event_type, json.dumps(payload), self._now()),
            )

    def add_signal(self, signal: dict[str, Any], reason: str = "") -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO signals(symbol,side,entry,stop_loss,take_profit,risk_reward,reason,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (signal.get("symbol", "XAUUSD"), signal.get("side"), signal.get("entry"),
                 signal.get("sl"), signal.get("tp"), signal.get("risk_reward"), reason, self._now()),
            )
            return int(cursor.lastrowid)

    def add_trade(self, signal: dict[str, Any], decision: dict[str, Any], ema_state: dict[str, Any] | None = None) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO trades(symbol,side,entry,stop_loss,take_profit,volume,status,reason,ema_state,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (signal.get("symbol", "XAUUSD"), signal["side"], signal["entry"], signal["sl"],
                 signal["tp"], decision.get("lot_size", 0), decision.get("status", "dry_run"),
                 signal.get("reason", ""), json.dumps(ema_state or {}), self._now()),
            )
            return int(cursor.lastrowid)

    def rows(self, table: str, limit: int = 100) -> list[dict[str, Any]]:
        if table not in {"trades", "signals", "agent_events", "daily_stats"}:
            raise ValueError("unsupported table")
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(
                f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()]

    def summary(self) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(pnl),0) pnl, COUNT(*) trades, "
                "COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END),0) wins FROM trades"
            ).fetchone()
        return {"pnl": row["pnl"], "trades": row["trades"], "wins": row["wins"],
                "win_rate": (row["wins"] / row["trades"] * 100) if row["trades"] else 0}