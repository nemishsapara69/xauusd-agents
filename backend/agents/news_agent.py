"""Economic-calendar filter with an injectable free-source adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

import requests


@dataclass(frozen=True)
class NewsEvent:
    timestamp: datetime
    currency: str
    impact: str
    title: str


class NewsAgent:
    def __init__(
        self,
        fetcher: Callable[[], Iterable[NewsEvent]] | None = None,
        summarizer: Callable[[NewsEvent], str] | None = None,
    ) -> None:
        self.fetcher = fetcher or self.fetch_calendar
        self.summarizer = summarizer or self.gemini_summary

    @staticmethod
    def gemini_summary(event: NewsEvent) -> str:
        """Return a short Gemini summary when configured, otherwise a factual fallback."""
        import os

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return f"High-impact USD event: {event.title}"
        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Summarize this trading calendar event in one neutral line: {event.title}",
            )
            text = (response.text or "").strip().replace("\n", " ")
            return text[:240] or f"High-impact USD event: {event.title}"
        except (ImportError, OSError, RuntimeError, ValueError):
            return f"High-impact USD event: {event.title}"

    @staticmethod
    def fetch_calendar() -> list[NewsEvent]:
        """Fetch events from the public Forex Factory calendar feed."""
        response = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            timeout=10,
        )
        response.raise_for_status()
        events = []
        for item in response.json():
            timestamp = datetime.fromisoformat(item["date"].replace("Z", "+00:00")).astimezone(timezone.utc)
            events.append(
                NewsEvent(
                    timestamp=timestamp,
                    currency=str(item.get("country", "")),
                    impact=str(item.get("impact", "")).lower(),
                    title=str(item.get("title", "")),
                )
            )
        return events

    def check(self, now: datetime | None = None) -> dict[str, Any]:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        try:
            events = self.fetcher()
        except requests.RequestException as exc:
            return {"trade_allowed": False, "event": None, "event_time": None,
                    "summary": f"News feed unavailable; trading blocked: {exc}"}
        relevant = [
            event for event in events
            if event.currency == "USD" and event.impact == "high"
            and any(term in event.title.upper() for term in ("CPI", "NFP", "FOMC"))
        ]
        blocked = next(
            (
                event
                for event in relevant
                if event.timestamp - timedelta(minutes=30) <= current <= event.timestamp + timedelta(minutes=30)
            ),
            None,
        )
        return {
            "trade_allowed": blocked is None,
            "event": blocked.title if blocked else None,
            "event_time": blocked.timestamp.isoformat() if blocked else None,
            "summary": self.summarizer(blocked) if blocked and self.summarizer else (
                f"High-impact USD event: {blocked.title}" if blocked else "No blocking USD news event."
            ),
        }