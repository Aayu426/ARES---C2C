"""Simulator transport: virtual witnesses A, B, C, WEBCAM reading a shared virtual
environment, signing frames with the same keys the real nodes use.

The engine cannot tell a simulated witness from a real one. Attacks are applied here in
`sim` mode so the whole demo runs with no hardware:
  suppress  - the node reports the claim as 0 regardless of the environment
  inject    - the node reports an impossible temperature
  drift     - the node's temperature offset grows a little every interval
  spoof     - frames are signed with the wrong key (an impostor)
  replay    - an old frame is re-sent verbatim
  restore   - back to honest, honest fingerprint again
"""
from __future__ import annotations

import asyncio
import random
import time

from ..canonical import sign, telemetry_canonical, witness_canonical, response_canonical
from .base import Transport

HONEST_FW = {
    "A": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "B": "b4a1d2c3e4f5061728394a5b6c7d8e9f0a1b2c3d4e5f60718293a4b5c6d7e8f9",
    "C": "c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2",
    "WEBCAM": "d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3",
}
TAMPERED_FW = "7a1c0000000000000000000000000000000000000000000000000000000000ff"


class VirtualNode:
    def __init__(self, node_id: str, key: bytes, claims: list[str], honest_fw: str | None = None) -> None:
        self.node_id = node_id
        self.key = key
        self.honest_fw = honest_fw or HONEST_FW.get(node_id, "")
        self.claims = claims          # which claims this node witnesses
        self.seq = 0
        self.boot = time.monotonic()
        self.mode: str | None = None  # None (honest) | suppress | inject | drift | spoof | replay
        self.inject_temp = 80.0
        self.drift = 0.0
        self.last_frame: dict | None = None
        self.replayed = 0

    @property
    def fw(self) -> str:
        return self.honest_fw if self.mode is None else TAMPERED_FW

    def ts(self) -> int:
        return int((time.monotonic() - self.boot) * 1000)


class SimTransport(Transport):
    name = "sim"

    def __init__(self, keys: dict[str, bytes], interval: float = 1.0, known_fw: dict[str, str] | None = None) -> None:
        super().__init__()
        self.interval = interval
        self.env = {"person": False, "water": False, "temp": 24.4}
        fw = known_fw or {}
        self.nodes_by_id: dict[str, VirtualNode] = {
            "A": VirtualNode("A", keys["A"], ["motion", "temp"], fw.get("A")),
            "B": VirtualNode("B", keys["B"], ["water"], fw.get("B")),
            "C": VirtualNode("C", keys["C"], ["motion", "water"], fw.get("C")),
            "WEBCAM": VirtualNode("WEBCAM", keys["WEBCAM"], ["motion", "water"], fw.get("WEBCAM")),
        }
        self._task: asyncio.Task | None = None
        self._running = False

    def nodes(self) -> list[str]:
        return list(self.nodes_by_id)

    async def start(self, loop: asyncio.AbstractEventLoop) -> None:
        await super().start(loop)
        self._running = True
        self._task = asyncio.create_task(self._run())
        print("[sim] virtual witnesses A, B, C, WEBCAM running")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    # ---- environment and attacks (called from the HTTP API) ----

    def set_env(self, **changes) -> dict:
        for k, v in changes.items():
            if k in self.env and v is not None:
                self.env[k] = v
        return dict(self.env)

    def attack(self, mode: str, target: str, temp: float | None = None) -> str:
        node = self.nodes_by_id.get(target)
        if node is None:
            return f"unknown target {target}"
        if mode == "restore":
            for n in self.nodes_by_id.values():
                n.mode, n.drift = None, 0.0
            return "all nodes honest again"
        node.mode = mode
        if mode == "inject" and temp is not None:
            node.inject_temp = temp
        if mode == "replay":
            node.replayed = 0
        return f"{target} now in {mode} mode"

    # ---- the tick loop ----

    async def _run(self) -> None:
        try:
            while self._running:
                for node in self.nodes_by_id.values():
                    for msg in self._frames_for(node):
                        await self._deliver(msg, "sim")
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            pass

    def _frames_for(self, node: VirtualNode) -> list[dict]:
        # replay: resend the last honest frame a few times, then fall through
        if node.mode == "replay" and node.last_frame is not None and node.replayed < 5:
            node.replayed += 1
            return [dict(node.last_frame)]

        node.seq += 1
        ts = node.ts()
        key = node.key if node.mode != "spoof" else b"\x00" * 32  # impostor has no key
        frames: list[dict] = []

        if node.node_id in ("A", "B"):
            msg: dict = {"t": "tel", "node_id": node.node_id, "seq": node.seq, "ts": ts}
            if "motion" in node.claims:
                motion = 1 if self.env["person"] else 0
                if node.mode == "suppress":
                    motion = 0
                msg["motion"] = motion
            if "temp" in node.claims:
                temp = self.env["temp"] + random.uniform(-0.15, 0.15)
                if node.mode == "inject":
                    temp = node.inject_temp
                if node.mode == "drift":
                    node.drift += 0.1
                    temp += node.drift
                msg["temp"] = round(temp, 2)
            if "water" in node.claims:
                water = 1 if self.env["water"] else 0
                if node.mode == "suppress":
                    water = 0
                msg["water"] = water
            msg["hmac"] = sign(key, telemetry_canonical(msg))
            frames.append(msg)
        else:
            # vision witnesses: one message per claim
            for claim in node.claims:
                truth = self.env["person"] if claim == "motion" else self.env["water"]
                value = 1 if truth else 0
                if node.mode == "suppress":
                    value = 0
                conf = round(random.uniform(0.86, 0.98), 2)
                msg = {"t": "wit", "node_id": node.node_id, "seq": node.seq, "ts": ts,
                       "claim": claim, "value": value, "conf": conf}
                msg["hmac"] = sign(key, witness_canonical(msg))
                frames.append(msg)
                node.seq += 1
            node.seq -= 1

        if node.mode is None and frames:
            node.last_frame = dict(frames[0])
        return frames

    # ---- challenges ----

    async def send(self, node_id: str, msg: dict) -> bool:
        node = self.nodes_by_id.get(node_id)
        if node is None:
            return False
        if msg.get("t") == "chal":
            asyncio.create_task(self._answer(node, msg))
            return True
        if msg.get("t") == "atk":
            self.attack(msg.get("mode", "restore"), node_id, msg.get("temp"))
            return True
        return True  # alarm etc. are accepted silently in sim

    async def _answer(self, node: VirtualNode, chal: dict) -> None:
        await asyncio.sleep(random.uniform(0.2, 0.8))
        fw = node.fw if chal.get("type") == "integrity" else ""
        key = node.key if node.mode != "spoof" else b"\x00" * 32
        sig = sign(key, response_canonical(node.node_id, chal["challenge_id"], chal["nonce"], fw))
        await self._deliver({"t": "resp", "node_id": node.node_id, "challenge_id": chal["challenge_id"],
                             "fw": fw, "sig": sig}, "sim")
