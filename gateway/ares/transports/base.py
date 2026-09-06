"""Transport interface. A transport delivers parsed NDJSON dicts from witnesses to the
engine and sends dicts back to a named node. Both real serial ports and the simulator
implement this, so the engine cannot tell them apart."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

Handler = Callable[[dict, str], Awaitable[None]]  # (message, source_label)


class Transport:
    name = "base"

    def __init__(self) -> None:
        self._handler: Handler | None = None
        self.loop: asyncio.AbstractEventLoop | None = None

    def on_message(self, handler: Handler) -> None:
        self._handler = handler

    async def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def stop(self) -> None:
        pass

    async def send(self, node_id: str, msg: dict) -> bool:
        """Deliver a dict to a node. Returns False if the node is unreachable."""
        return False

    def nodes(self) -> list[str]:
        return []

    async def _deliver(self, msg: dict, source: str) -> None:
        if self._handler is not None:
            await self._handler(msg, source)
