"""HTTP transport for laptop-side witnesses (the vision service) and a router that
combines several transports so serial boards and HTTP cameras share one engine.

Outbound messages for an HTTP node queue in an outbox the service polls
(GET /outbox/<node>); inbound messages arrive on POST /inbox."""
from __future__ import annotations

import asyncio
import time

from .base import Transport


class HttpTransport(Transport):
    name = "http"

    def __init__(self, node_ids: list[str], outbox_ttl: float = 10.0) -> None:
        super().__init__()
        self.node_ids = node_ids
        self.outbox: dict[str, list[tuple[float, dict]]] = {n: [] for n in node_ids}
        self.last_poll: dict[str, float] = {}
        self.ttl = outbox_ttl

    def nodes(self) -> list[str]:
        return [n for n in self.node_ids if n in self.last_poll]

    async def send(self, node_id: str, msg: dict) -> bool:
        if node_id not in self.outbox:
            return False
        # a node that has never polled, or stopped polling, is unreachable
        if time.time() - self.last_poll.get(node_id, 0) > self.ttl:
            return False
        self.outbox[node_id].append((time.time(), msg))
        return True

    def drain(self, node_id: str) -> list[dict]:
        self.last_poll[node_id] = time.time()
        now = time.time()
        items = self.outbox.get(node_id, [])
        fresh = [m for (t, m) in items if now - t <= self.ttl]
        if node_id in self.outbox:
            self.outbox[node_id] = []
        return fresh

    async def inbound(self, msg: dict) -> None:
        node_id = msg.get("node_id")
        if node_id in self.outbox:
            self.last_poll[node_id] = time.time()
        await self._deliver(msg, "http")


class MultiTransport(Transport):
    """Routes send() by node id; merges inbound from every child."""
    name = "multi"

    def __init__(self, routes: dict[str, Transport]) -> None:
        super().__init__()
        self.routes = routes
        self.children: list[Transport] = []
        for t in routes.values():
            if t not in self.children:
                self.children.append(t)

    def on_message(self, handler) -> None:
        super().on_message(handler)
        for t in self.children:
            t.on_message(handler)

    async def start(self, loop: asyncio.AbstractEventLoop) -> None:
        await super().start(loop)
        for t in self.children:
            await t.start(loop)

    async def stop(self) -> None:
        for t in self.children:
            await t.stop()

    def nodes(self) -> list[str]:
        out: list[str] = []
        for t in self.children:
            out.extend(t.nodes())
        return out

    async def send(self, node_id: str, msg: dict) -> bool:
        t = self.routes.get(node_id)
        return await t.send(node_id, msg) if t else False

    def child(self, cls):
        for t in self.children:
            if isinstance(t, cls):
                return t
        return None
