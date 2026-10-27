from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import yaml

from api.auth import current_user
from core.config import CONFIG_DIR

router = APIRouter(prefix="/api/control", tags=["control"], dependencies=[Depends(current_user)])
_state = {"running": True, "kill_switch": False, "close_all_requested": False}


class RiskRules(BaseModel):
    risk_per_trade_usd: float = 50.0
    max_daily_loss_usd: float = 1000.0
    max_open_positions: int = 10
    max_spread_points: float
    min_risk_reward: float = 2.0
    stop_loss_pips: float = 50.0
    max_take_profit_pips: float = 100.0
    pip_size: float = 0.01


@router.get("/status")
def status() -> dict:
    from core.config import load_config

    config = load_config()
    return {
        **_state,
        "execution_enabled": config.execution_enabled,
    }


@router.post("/toggle")
def toggle() -> dict:
    _state["running"] = not _state["running"]
    if _state["running"]:
        _state["kill_switch"] = False
    return dict(_state)


@router.get("/risk-rules")
def risk_rules() -> dict:
    path = CONFIG_DIR / "risk_rules.yaml"
    try:
        values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Unable to read risk rules") from exc
    return values


@router.post("/start")
def start() -> dict:
    _state.update(running=True, kill_switch=False)
    return dict(_state)


@router.post("/stop")
def stop() -> dict:
    _state["running"] = False
    return dict(_state)


@router.post("/kill-switch")
def kill_switch(close_all: bool = False) -> dict:
    _state.update(running=False, kill_switch=True, close_all_requested=close_all)
    return dict(_state)


@router.post("/risk-rules")
def update_risk_rules(rules: RiskRules) -> dict:
    if rules.risk_per_trade_usd <= 0 or rules.max_daily_loss_usd <= 0:
        raise HTTPException(status_code=400, detail="Risk amounts must be positive")
    if (
        rules.max_open_positions < 1
        or rules.max_open_positions > 10
        or rules.max_spread_points <= 0
        or rules.min_risk_reward <= 0
        or rules.stop_loss_pips <= 0
        or rules.max_take_profit_pips <= 0
        or rules.pip_size <= 0
    ):
        raise HTTPException(status_code=400, detail="Position limit must be between 1 and 10; other limits are invalid")
    values = rules.dict() if hasattr(rules, "dict") else rules.model_dump()
    (CONFIG_DIR / "risk_rules.yaml").write_text(
        yaml.safe_dump(values, sort_keys=False), encoding="utf-8"
    )
    return values


def trading_allowed() -> bool:
    return bool(_state["running"] and not _state["kill_switch"])