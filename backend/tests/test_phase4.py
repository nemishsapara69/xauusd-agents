from datetime import datetime, timezone
from pathlib import Path

from agents.reporting_agent import ReportingAgent
from core.scheduler import CandleCloseScheduler
from database.db import Database


def test_database_trade_round_trip(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    signal = {"symbol": "XAUUSD", "side": "buy", "entry": 2000, "sl": 1990, "tp": 2020}
    trade_id = database.add_trade(signal, {"lot_size": 0.1, "status": "dry_run"})
    assert trade_id > 0
    assert database.rows("trades")[0]["symbol"] == "XAUUSD"


def test_scheduler_only_accepts_new_candle() -> None:
    scheduler = CandleCloseScheduler()
    timestamp = datetime.now(timezone.utc)
    assert scheduler.is_new_candle(timestamp)
    assert not scheduler.is_new_candle(timestamp)


def test_report_from_fake_trades(tmp_path: Path) -> None:
    database = Database(tmp_path / "report.sqlite3")
    database.add_trade({"symbol": "XAUUSD", "side": "buy", "entry": 1, "sl": 0, "tp": 2}, {"lot_size": 1, "status": "dry_run"})
    with database.connect() as connection:
        connection.execute("UPDATE trades SET pnl = 25")
    report = ReportingAgent(database).report("weekly")
    assert report["pnl"] == 25
    assert report["trades"] == 1
