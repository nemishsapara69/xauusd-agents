from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from api.auth import current_user
from core.config import ConfigurationError
from core.mt5_client import MT5Client, MT5ClientError
from database.db import Database

router = APIRouter(prefix="/api", tags=["dashboard"], dependencies=[Depends(current_user)])
database = Database()


@router.get("/trades")
def trades(limit: int = Query(100, ge=1, le=1000)) -> dict:
    client = None
    try:
        client = MT5Client()
        client.connect()
        positions = client.get_positions()
        live = [{
            "id": f"mt5-{position.get('ticket')}",
            "created_at": datetime.fromtimestamp(position["time"], timezone.utc).isoformat(),
            "symbol": position.get("symbol"),
            "side": "buy" if position.get("type") == 0 else "sell",
            "entry": position.get("price_open"),
            "stop_loss": position.get("sl"),
            "take_profit": position.get("tp"),
            "volume": position.get("volume"),
            "pnl": position.get("profit"),
            "status": "open",
            "source": "MT5",
        } for position in positions]
        return {"trades": live[:limit], "source": "MT5"}
    except (ConfigurationError, MT5ClientError, OSError, AttributeError):
        return {"trades": [], "source": "MT5 unavailable"}
    finally:
        if client is not None:
            client.close()


@router.get("/chart-trades")
def chart_trades(days: int = Query(30, ge=1, le=90)) -> dict:
    client = None
    try:
        client = MT5Client()
        client.connect()
        symbol = client.config.symbol
        positions = client.get_positions()
        deals = client.get_deals(
            datetime.now(timezone.utc) - timedelta(days=days),
            datetime.now(timezone.utc),
            symbol=symbol,
        )
        markers = []
        for position in positions:
            markers.append({
                "id": f"position-{position.get('ticket')}",
                "time": int(position["time"]),
                "price": float(position["price_open"]),
                "side": "buy" if position.get("type") == 0 else "sell",
                "kind": "entry",
                "status": "open",
            })
        for deal in deals:
            entry_type = deal.get("entry")
            if entry_type not in {0, 1} or float(deal.get("price", 0) or 0) <= 0:
                continue
            markers.append({
                "id": f"deal-{deal.get('ticket')}",
                "time": int(deal["time"]),
                "price": float(deal["price"]),
                "side": "buy" if deal.get("type") == 0 else "sell",
                "kind": "entry" if entry_type == 0 else "exit",
                "status": "closed" if entry_type == 1 else "filled",
                "profit": float(deal.get("profit", 0) or 0),
            })
        return {"trades": markers, "source": "MT5"}
    except (ConfigurationError, MT5ClientError, OSError, AttributeError):
        return {"trades": [], "source": "MT5 unavailable"}
    finally:
        if client is not None:
            client.close()


@router.get("/reports")
def reports(period: str = Query("daily", pattern="^(daily|weekly)$")) -> dict:
    from agents.reporting_agent import ReportingAgent

    return ReportingAgent(database).report(period)


@router.get("/logs")
def logs(limit: int = Query(100, ge=1, le=1000)) -> dict:
    return {"events": database.rows("agent_events", limit)}


@router.get("/dashboard")
def dashboard() -> dict:
    from core.config import load_config

    summary = database.summary()
    balance = None
    equity = None
    account_status = "unavailable"
    account_currency = None
    account_server = None
    client = None
    try:
        client = MT5Client()
        client.connect()
        account = client.get_account()
        balance = account.get("balance")
        equity = account.get("equity")
        account_currency = account.get("currency")
        account_server = account.get("server")
        account_status = "connected"
        client.close()
    except (ConfigurationError, MT5ClientError, OSError, AttributeError):
        balance = None
        equity = None
    finally:
        if client is not None:
            client.close()
    return {
        "balance": balance,
        "equity": equity,
        "account_status": account_status,
        "account_currency": account_currency,
        "account_server": account_server,
        "execution_enabled": load_config().execution_enabled,
        "today_pnl": summary["pnl"],
        "open_trades": len([row for row in database.rows("trades", 1000) if row["status"] == "open"]),
        **summary,
    }
