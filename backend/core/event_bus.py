"""In-process asynchronous event bus."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: set[EventHandler] = set()

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.add(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        self._handlers.discard(handler)

    async def publish(self, event: dict[str, Any]) -> None:
        if not isinstance(event, dict) or not event.get("type"):
            raise ValueError("event must be a dictionary with a type")
        await asyncio.gather(*(handler(event) for handler in tuple(self._handlers)))