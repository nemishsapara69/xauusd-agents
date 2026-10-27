from __future__ import annotations

from datetime import datetime


class CandleCloseScheduler:
    """Runs a callback once for each observed candle timestamp."""

    def __init__(self) -> None:
        self.last_timestamp: datetime | None = None

    def is_new_candle(self, timestamp: datetime) -> bool:
        if self.last_timestamp == timestamp:
            return False
        self.last_timestamp = timestamp
        return True