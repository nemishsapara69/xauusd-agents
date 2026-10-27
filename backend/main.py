import asyncio
import os
from datetime import datetime, time, timezone, timezone
from typing import Optional

from fastapi import Depends, FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError

from api.candles import router as candles_router
from api.auth import current_user, router as auth_router
from api.control import router as control_router, trading_allowed
from api.dashboard import router as dashboard_router
from agents.analysis_agent import analyze
from agents.level_agent import find_signal
from core.config import ConfigurationError
from core.event_bus import EventBus
from core.logger import setup_logging
from core.indicators import add_emas
from core.mt5_client import MT5Client, MT5ClientError, Timeframe
from core.orchestrator import Orchestrator
from core.scheduler import CandleCloseScheduler
from ws.manager import ConnectionManager

app = FastAPI(title="XAUUSD Agents")
app.include_router(auth_router)
app.include_router(candles_router)
app.include_router(dashboard_router)
app.include_router(control_router)
logger = setup_logging()
event_bus = EventBus()
connection_manager = ConnectionManager()
orchestrator = Orchestrator(event_bus)
scheduler = CandleCloseScheduler()
event_bus.subscribe(connection_manager.broadcast)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", dependencies=[Depends(current_user)])
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    try:
        current_user_from_token(token)
    except (RuntimeError, ValueError, JWTError):
        await websocket.close(code=1008, reason="Authentication required")
        return
    await connection_manager.connect(websocket)
    await connection_manager.receive_until_disconnect(websocket)


def current_user_from_token(token: Optional[str]) -> str:
    from api.auth import _secret
    from jose import jwt

    if not token:
        raise RuntimeError("missing token")
    payload = jwt.decode(token, _secret(), algorithms=["HS256"])
    username = payload.get("sub")
    if not username:
        raise RuntimeError("invalid token")
    return str(username)


async def publish_event(event_type: str, payload: dict) -> None:
    event = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    await event_bus.publish(event)


async def _market_data_loop() -> None:
    client: MT5Client | None = None
    while True:
        try:
            if client is None:
                client = MT5Client()
                client.connect()
            frames = {}
            for timeframe in Timeframe:
                frame = add_emas(client.get_candles(client.config.symbol, timeframe, client.config.candle_count, True))
                frames[timeframe.value] = frame
                candle = frame.iloc[-1].where(frame.iloc[-1].notna(), None).to_dict()
                for key, value in candle.items():
                    if hasattr(value, "item"):
                        candle[key] = value.item()
                candle["time"] = candle["time"].isoformat()
                await publish_event(
                    "candle_update",
                    {"symbol": client.config.symbol, "timeframe": timeframe.value, "candle": candle},
                )
            account = client.get_account()
            account_payload = {
                key: value
                for key, value in account.items()
                if key in {"balance", "equity", "profit", "margin", "margin_free", "currency", "server"}
            }
            await publish_event("account_update", account_payload)
            trend = analyze(frames["M15"], frames["H1"])
            signal = find_signal(frames["M15"], trend["trend"], client.config.symbol)
            await publish_event(
                "agent_update",
                {"agent": "analysis", "result": trend, "signal": signal},
            )
            closed_frames = {key: frame.iloc[:-1].copy() for key, frame in frames.items()}
            m15_time = closed_frames["M15"].iloc[-1]["time"].to_pydatetime()
            if scheduler.is_new_candle(m15_time) and trading_allowed():
                positions = client.get_positions(client.config.symbol)
                now = datetime.now(timezone.utc)
                start_of_day = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
                deals = client.get_deals(start_of_day, now, client.config.symbol)
                realized_loss = abs(sum(
                    min(float(deal.get("profit", 0.0)), 0.0)
                    for deal in deals
                ))
                await orchestrator.run(
                    closed_frames,
                    client.config.symbol,
                    daily_loss_usd=realized_loss,
                    open_positions=len(positions),
                )
        except (ConfigurationError, MT5ClientError, ValueError) as exc:
            logger.warning("Market data update unavailable: %s", exc)
            if client is not None:
                client.close()
                client = None
        await asyncio.sleep(1)


@app.on_event("startup")
async def start_market_data_loop() -> None:
    app.state.market_data_task = asyncio.create_task(_market_data_loop())


@app.on_event("shutdown")
async def stop_market_data_loop() -> None:
    task = getattr(app.state, "market_data_task", None)
    if task is not None:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    MT5Client.shutdown()