from datetime import datetime, timezone
import os

import pandas as pd
from fastapi.testclient import TestClient

from api.auth import create_token
from api.control import _state
from backtest.backtester import run_backtest
from main import app


def test_api_requires_authentication() -> None:
    client = TestClient(app)
    assert client.get("/api/health").status_code == 401
    assert client.get("/api/dashboard").status_code == 401


def test_jwt_token_allows_protected_api(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough")
    token = create_token("tester")
    client = TestClient(app)
    response = client.get("/api/control/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_kill_switch_blocks_orchestrator_state() -> None:
    _state.update(running=False, kill_switch=True)
    assert not __import__("api.control", fromlist=["trading_allowed"]).trading_allowed()
    _state.update(running=True, kill_switch=False)


def test_backtester_returns_required_metrics() -> None:
    timestamps = pd.date_range("2025-01-01", periods=260, freq="15min", tz="UTC")
    close = pd.Series(range(100, 360), dtype=float)
    frame = pd.DataFrame({"time": timestamps, "open": close, "high": close + 1, "low": close - 1, "close": close})
    result = run_backtest(frame, frame, frame)
    assert {"win_rate", "profit_factor", "max_drawdown", "equity_curve"} <= result.keys()
