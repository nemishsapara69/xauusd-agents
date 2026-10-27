from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import current_user
from core.config import ConfigurationError
from core.indicators import add_emas
from core.mt5_client import MT5Client, MT5ClientError, Timeframe

router = APIRouter(prefix="/api", tags=["market data"])
_VALID_TIMEFRAMES = {timeframe.value for timeframe in Timeframe}


@router.get("/candles", dependencies=[Depends(current_user)])
def candles(
    tf: str = Query("M15", description="MT5 timeframe"),
    count: int = Query(500, ge=1, le=5000),
) -> dict:
    timeframe = tf.upper()
    if timeframe not in _VALID_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe. Use one of: {', '.join(sorted(_VALID_TIMEFRAMES))}",
        )

    client: MT5Client | None = None
    try:
        client = MT5Client()
        client.connect()
        frame = add_emas(client.get_candles(client.config.symbol, timeframe, count))
        records = frame.astype(object).where(frame.notna(), None).to_dict(orient="records")
        for record in records:
            record["time"] = record["time"].isoformat()
            for key, value in record.items():
                if hasattr(value, "item"):
                    record[key] = value.item()
        return {
            "symbol": client.config.symbol,
            "timeframe": timeframe,
            "count": len(records),
            "candles": records,
        }
    except (ConfigurationError, MT5ClientError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        if client is not None:
            client.close()