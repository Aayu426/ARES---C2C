"""FastAPI application: WebSocket feed for the dashboard, HTTP for the vision service,
the judge attack panel and the simulator environment."""
from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .bus import EventBus
from .challenges import load_known_fw
from .engine import Engine, load_keys
from .store import Store
from .transports.base import Transport
from .transports.http_transport import HttpTransport, MultiTransport
from .transports.serial_transport import SerialTransport
from .transports.sim_transport import SimTransport


class AttackBody(BaseModel):
    type: str
    target: str | None = None
    temp: float | None = None


class EnvBody(BaseModel):
    person: bool | None = None
    water: bool | None = None
    temp: float | None = None


def create_app(mode: str = "sim", ports: list[str] | None = None, keys_path: str = "keys.json",
               db_path: str = "ares.db", sim_interval: float = 1.0, known_fw_path: str = "known_fw.json",
               **challenge_opts) -> FastAPI:
    keys = load_keys(keys_path)
    store = Store(db_path)
    bus = EventBus()
    if mode == "sim":
        transport: Transport = SimTransport(keys, sim_interval)
    else:
        serial_t = SerialTransport(ports or [])
        http_t = HttpTransport(["C", "WEBCAM"])
        transport = MultiTransport({"A": serial_t, "B": serial_t, "C": http_t, "WEBCAM": http_t})
    engine = Engine(transport, store, bus, keys, mode, known_fw=load_known_fw(known_fw_path), **challenge_opts)

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        await transport.start(asyncio.get_running_loop())
        await engine.start()
        print(f"[ares] gateway up in {mode} mode")
        yield
        await engine.stop()
        await transport.stop()

    app = FastAPI(title="ARES gateway", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.state.engine = engine
    app.state.bus = bus
    app.state.transport = transport

    @app.get("/health")
    async def health():
        return {"ok": True, "mode": mode, "nodes": transport.nodes()}

    @app.get("/state")
    async def state():
        return engine.state()

    @app.post("/witness")
    async def witness(msg: dict):
        """Vision service posts CONTRACTS 3.2 messages here (serial mode)."""
        if msg.get("t") != "wit":
            raise HTTPException(400, "expected a witness message (t == 'wit')")
        http_t = transport.child(HttpTransport) if isinstance(transport, MultiTransport) else None
        if http_t is not None:
            await http_t.inbound(msg)
        else:
            await engine.on_message(msg, "http")
        return {"ok": True}

    @app.get("/outbox/{node_id}")
    async def outbox(node_id: str):
        """Vision service polls this for challenges and attack commands (serial mode)."""
        http_t = transport.child(HttpTransport) if isinstance(transport, MultiTransport) else None
        if http_t is None:
            return []
        return http_t.drain(node_id)

    @app.post("/inbox")
    async def inbox(msg: dict):
        """Vision service posts challenge responses (and may post witnesses) here."""
        if msg.get("t") not in ("wit", "resp", "tel"):
            raise HTTPException(400, "expected t == 'wit', 'resp' or 'tel'")
        http_t = transport.child(HttpTransport) if isinstance(transport, MultiTransport) else None
        if http_t is not None:
            await http_t.inbound(msg)
        else:
            await engine.on_message(msg, "http")
        return {"ok": True}

    @app.get("/capture/{node_id}")
    async def capture(node_id: str, n: int = 5):
        """Last valid raw frames from a node, signatures included: what an attacker on the
        wire would have captured. Used by attacks/replay.py."""
        return store.recent_telemetry(node_id, n)

    @app.post("/attack")
    async def attack(body: AttackBody):
        result = await engine.attack(body.type, body.target or "A", body.temp)
        return {"ok": True, "result": result}

    @app.post("/sim/env")
    async def sim_env(body: EnvBody):
        """Simulated world: set person / water / temp so the demo runs with no hardware."""
        if not isinstance(transport, SimTransport):
            raise HTTPException(400, "not in sim mode")
        return {"ok": True, "env": transport.set_env(person=body.person, water=body.water, temp=body.temp)}

    @app.get("/events/recent")
    async def recent():
        return bus.recent[-200:]

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        q = bus.subscribe()
        try:
            # initial snapshot so a late-joining dashboard is never blank
            await socket.send_text(EventBus.encode({"e": "snapshot", **engine.state()}))
            while True:
                event = await q.get()
                await socket.send_text(EventBus.encode(event))
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe(q)

    return app
