"""The ARES engine, Phase 1 scope: ingest, verify signatures, normalise everything into
witnesses, persist, broadcast. Trust scoring, challenges and consensus arrive in
Phase 2 and 3 and plug into `NodeRecord` and `on_witness`.

Everything the engine sees is a *witness*: node A's `motion: 1` and camera C's
`{claim: motion, value: 1}` become the same shape. That is the whole design."""
from __future__ import annotations

import json
import os
import time
import uuid

from .bus import EventBus
from .canonical import new_key_hex, telemetry_canonical, verify, witness_canonical
from .store import Store
from .transports.base import Transport

NODE_IDS = ["A", "B", "C", "WEBCAM"]
CLAIMS_OF = {"A": ["motion", "temp"], "B": ["water"], "C": ["motion", "water"], "WEBCAM": ["motion", "water"]}


def load_keys(path: str) -> dict[str, bytes]:
    """Load per-node keys; create the file with fresh random keys if missing.
    The same file is copied (never committed) to the firmware secrets header and the
    vision service."""
    if not os.path.exists(path):
        keys = {n: new_key_hex() for n in NODE_IDS}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(keys, fh, indent=2)
        print(f"[keys] generated new keys in {path} — copy them to firmware/secrets.h and vision/keys.json")
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {n: bytes.fromhex(k) for n, k in raw.items()}


class NodeRecord:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.claims = CLAIMS_OF.get(node_id, [])
        self.last_seen: float | None = None
        self.last_seq: int | None = None
        self.last: dict = {}
        self.hmac_failures = 0
        self.frames = 0
        # trust vector — Phase 2 replaces these constants with real scoring
        self.identity = 100.0
        self.integrity = 100.0
        self.consistency = 100.0
        self.state = "TRUSTED"
        self.recovery: str | None = None

    @property
    def overall(self) -> float:
        return round(0.35 * self.identity + 0.35 * self.integrity + 0.30 * self.consistency, 1)

    def snapshot(self) -> dict:
        return {
            "e": "node_update", "node_id": self.node_id, "state": self.state,
            "identity": round(self.identity), "integrity": round(self.integrity),
            "consistency": round(self.consistency), "overall": self.overall,
            "recovery": self.recovery, "last": dict(self.last),
            "last_seen": self.last_seen, "online": self.online,
        }

    @property
    def online(self) -> bool:
        return self.last_seen is not None and (time.time() - self.last_seen) < 5.0


class Engine:
    def __init__(self, transport: Transport, store: Store, bus: EventBus, keys: dict[str, bytes], mode: str) -> None:
        self.transport = transport
        self.store = store
        self.bus = bus
        self.keys = keys
        self.mode = mode
        self.nodes: dict[str, NodeRecord] = {n: NodeRecord(n) for n in NODE_IDS}
        self.claims: dict[str, dict] = {"motion": {"status": "CLEAR", "by": [], "against": []},
                                        "water": {"status": "CLEAR", "by": [], "against": []}}
        self.alarm = {"on": False, "reason": "baseline"}
        transport.on_message(self.on_message)

    # ---- inbound ----

    async def on_message(self, msg: dict, source: str) -> None:
        kind = msg.get("t")
        node_id = msg.get("node_id")
        if node_id not in self.nodes:
            return
        node = self.nodes[node_id]
        if kind == "tel":
            await self._on_telemetry(node, msg)
        elif kind == "wit":
            await self._on_witness_msg(node, msg)
        elif kind == "resp":
            await self.on_challenge_response(node, msg)   # Phase 2

    async def _on_telemetry(self, node: NodeRecord, msg: dict) -> None:
        ok = verify(self.keys[node.node_id], telemetry_canonical(msg), msg.get("hmac"))
        self._touch(node, msg, ok)
        self.store.add_telemetry(msg, ok)
        if not ok:
            self._identity_failure(node, "invalid signature on telemetry frame")
            return
        for claim in ("motion", "water", "temp"):
            if claim in msg:
                node.last[claim] = msg[claim]
                await self.on_witness(node, claim, float(msg[claim]), 1.0, ok)
        self.bus.publish(node.snapshot())

    async def _on_witness_msg(self, node: NodeRecord, msg: dict) -> None:
        ok = verify(self.keys[node.node_id], witness_canonical(msg), msg.get("hmac"))
        self._touch(node, msg, ok)
        if not ok:
            self._identity_failure(node, "invalid signature on witness message")
            return
        claim = msg.get("claim")
        if claim not in ("motion", "water"):
            return
        node.last[claim] = int(msg.get("value", 0))
        await self.on_witness(node, claim, float(msg.get("value", 0)), float(msg.get("conf", 1.0)), ok)
        self.bus.publish(node.snapshot())

    def _touch(self, node: NodeRecord, msg: dict, ok: bool) -> None:
        node.last_seen = time.time()
        node.frames += 1
        seq = msg.get("seq")
        if isinstance(seq, int):
            node.last_seq = seq
        if not ok:
            node.hmac_failures += 1

    def _identity_failure(self, node: NodeRecord, detail: str) -> None:
        # Phase 1: a bad signature is the one thing we already score. Phase 2 folds this
        # into the debt table; Phase 4 adds the replay window on seq/ts.
        node.identity = 0.0
        self.bus.publish({"e": "identity_failure", "node_id": node.node_id, "detail": detail})
        self.bus.publish(node.snapshot())

    async def on_witness(self, node: NodeRecord, claim: str, value: float, conf: float, hmac_ok: bool) -> None:
        """Every reading, real or simulated, sensor or camera, lands here as a witness.
        Phase 2 adds consistency + physics scoring; Phase 3 adds consensus."""
        self.store.add_witness(node.node_id, claim, value, conf, hmac_ok)
        self.bus.publish({"e": "witness", "node_id": node.node_id, "claim": claim,
                          "value": value, "conf": conf})

    async def on_challenge_response(self, node: NodeRecord, msg: dict) -> None:
        # Phase 2 verifies the signature and closes the challenge.
        self.bus.publish({"e": "challenge_response_raw", "node_id": node.node_id,
                          "challenge_id": msg.get("challenge_id")})

    # ---- outbound / control ----

    async def attack(self, type_: str, target: str, temp: float | None = None) -> str:
        """Judge attack panel entry point. `type_` per CONTRACTS.md 8.1."""
        mapping = {"suppress_motion": ("suppress", "A"), "suppress_water": ("suppress", "B"),
                   "spoof": ("spoof", target or "A"), "replay": ("replay", target or "A"),
                   "inject": ("inject", "A"), "drift": ("drift", "A"), "restore": ("restore", target or "A")}
        if type_ not in mapping:
            return f"unknown attack {type_}"
        mode, node_id = mapping[type_]
        self.bus.publish({"e": "incident", "id": f"atk-{uuid.uuid4().hex[:6]}", "claim": "attack",
                          "summary": f"judge pressed {type_.upper()} on {node_id}"})
        msg = {"t": "atk", "mode": mode}
        if temp is not None:
            msg["temp"] = temp
        if type_ == "restore":
            for n in self.nodes.values():
                if n.identity == 0.0:
                    n.identity = 100.0  # Phase 2 replaces with RECOVERING gating
            reached = [n for n in self.nodes if await self.transport.send(n, msg)]
            return f"restore sent to {', '.join(reached) or 'nobody'}"
        sent = await self.transport.send(node_id, msg)
        return f"{mode} sent to {node_id}" if sent else f"{node_id} unreachable"

    def state(self) -> dict:
        return {"mode": self.mode, "nodes": {n: r.snapshot() for n, r in self.nodes.items()},
                "claims": self.claims, "alarm": self.alarm,
                "incidents": self.store.recent_incidents(20), "time": time.time()}
