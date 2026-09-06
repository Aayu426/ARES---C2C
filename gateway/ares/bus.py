"""In-process event bus. Everything the dashboard sees goes through `publish`.

Events follow CONTRACTS.md section 8.2. WebSocket clients each get their own queue so
a slow client never blocks the engine."""
from __future__ import annotations

import asyncio
import json
import time


class EventBus:
    def __init__(self, history: int = 500) -> None:
        self._queues: set[asyncio.Queue] = set()
        self.recent: list[dict] = []
        self._history = history

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)

    def publish(self, event: dict) -> None:
        event.setdefault("at", time.time())
        self.recent.append(event)
        if len(self.recent) > self._history:
            del self.recent[: len(self.recent) - self._history]
        for q in list(self._queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # drop the oldest for that client rather than stall the engine
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    @staticmethod
    def encode(event: dict) -> str:
        return json.dumps(event, separators=(",", ":"), default=str)
