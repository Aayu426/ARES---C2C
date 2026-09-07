"""Adaptive Challenge Engine. CONTRACTS.md sections 3.3, 3.4 and 6.

The type of doubt picks the challenge:
  signature trouble               -> identity  (sign a fresh nonce)
  outlier with a clean identity   -> integrity (report the firmware fingerprint)
  both pass but still an outlier  -> escalate: authentic, unmodified, isolated
Shadowed nodes are re-tested every 10 s, recovering nodes every 5 s; every pass while
recovering counts toward the 10 needed before the vote counts again."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import TYPE_CHECKING

from .canonical import new_nonce, response_canonical, verify

if TYPE_CHECKING:  # pragma: no cover
    from .engine import Engine, NodeRecord

CHALLENGE_TIMEOUT = 2.0
ATTEST_INTERVAL = 12.0          # periodic firmware attestation of every healthy node (sleeper-compromise catch)
SUSPICIOUS_RETRY = 3.0
SHADOW_RETRY = 10.0
RECOVERY_RETRY = 5.0

DEFAULT_KNOWN_FW = {
    "A": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "B": "b4a1d2c3e4f5061728394a5b6c7d8e9f0a1b2c3d4e5f60718293a4b5c6d7e8f9",
    "C": "c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2",
    "WEBCAM": "d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3",
}


def load_known_fw(path: str) -> dict[str, str]:
    """Known-good firmware fingerprints. Aayush overwrites this file with the hashes of
    the honest builds; the defaults match the simulator."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return {**DEFAULT_KNOWN_FW, **data}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(DEFAULT_KNOWN_FW, fh, indent=2)
    return dict(DEFAULT_KNOWN_FW)


class Pending:
    def __init__(self, challenge_id: str, node_id: str, type_: str, nonce: str, reason: str) -> None:
        self.challenge_id = challenge_id
        self.node_id = node_id
        self.type = type_
        self.nonce = nonce
        self.reason = reason
        self.issued_at = time.time()


class ChallengeEngine:
    def __init__(self, engine: "Engine", known_fw: dict[str, str],
                 suspicious_retry: float = SUSPICIOUS_RETRY, shadow_retry: float = SHADOW_RETRY,
                 recovery_retry: float = RECOVERY_RETRY, timeout: float = CHALLENGE_TIMEOUT,
                 attest_interval: float = ATTEST_INTERVAL) -> None:
        self.engine = engine
        self.known_fw = known_fw
        self.suspicious_retry = suspicious_retry
        self.shadow_retry = shadow_retry
        self.recovery_retry = recovery_retry
        self.timeout = timeout
        self.attest_interval = attest_interval
        self.last_attest: dict[str, float] = {}
        self.pending: dict[str, Pending] = {}
        self.last_issued: dict[str, float] = {}
        self.last_type: dict[str, str] = {}
        self.escalated: set[str] = set()
        self._task: asyncio.Task | None = None

    # ---- lifecycle ----

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(0.5)
                try:
                    await self._expire()
                    await self._schedule()
                except Exception as exc:  # never let the scheduler die
                    print(f"[challenge] loop error: {exc!r}")
        except asyncio.CancelledError:
            pass

    # ---- choosing ----

    def pick(self, node: "NodeRecord") -> tuple[str, str] | None:
        """Return (type, reason) for the next challenge, or None to hold off."""
        t = node.trust
        state = t.state
        if state in ("SHADOW", "RECOVERING"):
            nxt = "integrity" if self.last_type.get(node.node_id) == "identity" else "identity"
            label = "shadowed node re-tested" if state == "SHADOW" else f"recovery {t.recovery_label}"
            return nxt, f"{label}: {nxt} check"
        if state != "SUSPICIOUS":
            return None
        if node.hmac_failures and t.identity < 100:
            return "identity", f"signature errors on {node.node_id} -> proving identity"
        if t.consistency < 100 and self.last_type.get(node.node_id) != "integrity":
            claims = [c for c, n in node.disagree_cycles.items() if n > 0] or ["a claim"]
            return "integrity", (f"{node.node_id} disagrees with the other witnesses on {', '.join(claims)} "
                                 f"-> checking firmware, not identity")
        if self.last_type.get(node.node_id) == "integrity" and t.integrity == 100:
            if node.node_id not in self.escalated:
                self.escalated.add(node.node_id)
                self.engine.bus.publish({"e": "escalation", "node_id": node.node_id,
                                         "reason": f"{node.node_id} is authentic and unmodified but isolated on its claim -> human decision"})
            return "identity", "isolated but verified: alternating re-checks"
        return "integrity", "re-checking firmware"

    async def _attest_sweep(self, now: float) -> None:
        """Periodic firmware attestation of TRUSTED nodes. This is the layer that catches a
        SLEEPER / dormant compromise: a node whose data looks perfectly normal but whose
        firmware was tampered to await a later coordinated strike. Data-anomaly and consensus
        detection never flag such a node, so we attest EVERY healthy node on a fixed cadence and
        compare its fingerprint to the known-good baseline. The firmware fingerprint is the one
        parameter common to every sensor and sensitive to compromise regardless of its readings."""
        for node in self.engine.nodes.values():
            if node.trust.state != "TRUSTED" or node.last_seen is None:
                continue
            if any(p.node_id == node.node_id for p in self.pending.values()):
                continue
            if now - self.last_attest.get(node.node_id, 0) < self.attest_interval:
                continue
            self.last_attest[node.node_id] = now
            await self.issue(node, "integrity", "scheduled firmware attestation sweep")

    async def _schedule(self) -> None:
        now = time.time()
        await self._attest_sweep(now)
        for node in self.engine.nodes.values():
            if any(p.node_id == node.node_id for p in self.pending.values()):
                continue
            state = node.trust.state
            retry = {"SUSPICIOUS": self.suspicious_retry, "SHADOW": self.shadow_retry,
                     "RECOVERING": self.recovery_retry}.get(state)
            if retry is None:
                self.escalated.discard(node.node_id)
                continue
            if now - self.last_issued.get(node.node_id, 0) < retry:
                continue
            choice = self.pick(node)
            if choice:
                await self.issue(node, *choice)

    # ---- issuing and resolving ----

    async def issue(self, node: "NodeRecord", type_: str, reason: str) -> str:
        cid = f"c-{uuid.uuid4().hex[:6]}"
        nonce = new_nonce()
        self.pending[cid] = Pending(cid, node.node_id, type_, nonce, reason)
        self.last_issued[node.node_id] = time.time()
        self.last_type[node.node_id] = type_
        self.engine.store.add_challenge(cid, node.node_id, type_, nonce, reason)
        self.engine.bus.publish({"e": "challenge_issued", "node_id": node.node_id, "challenge_id": cid,
                                 "type": type_, "reason": reason})
        sent = await self.engine.transport.send(node.node_id, {"t": "chal", "challenge_id": cid,
                                                               "type": type_, "nonce": nonce})
        if not sent:
            await self._resolve(cid, False, "node unreachable")
        return cid

    async def on_response(self, node: "NodeRecord", msg: dict) -> None:
        cid = str(msg.get("challenge_id", ""))
        p = self.pending.get(cid)
        if p is None or p.node_id != node.node_id:
            self.engine.bus.publish({"e": "challenge_result", "node_id": node.node_id, "challenge_id": cid,
                                     "type": "?", "passed": False, "detail": "response to unknown or expired challenge"})
            return
        fw = str(msg.get("fw", "") or "")
        sig_ok = verify(self.engine.keys[node.node_id], response_canonical(node.node_id, cid, p.nonce, fw), msg.get("sig"))
        if not sig_ok:
            await self._resolve(cid, False, "response signature invalid: impostor")
            return
        if p.type == "identity":
            await self._resolve(cid, True, "nonce signed with the node's key: identity real")
            return
        expected = self.known_fw.get(node.node_id, "")
        if getattr(node, "forced_tamper", False):
            await self._resolve(cid, False, "firmware fingerprint tampered by injected compromise: does not match known-good")
        elif fw and fw == expected:
            await self._resolve(cid, True, "firmware fingerprint matches known-good")
        else:
            await self._resolve(cid, False, f"fingerprint {fw[:8]}… does not match known-good {expected[:8]}…: authentic but tampered")

    async def _expire(self) -> None:
        now = time.time()
        for cid, p in list(self.pending.items()):
            if now - p.issued_at > self.timeout:
                await self._resolve(cid, False, f"no response within {self.timeout:.0f} s")

    async def _resolve(self, cid: str, passed: bool, detail: str) -> None:
        p = self.pending.pop(cid, None)
        if p is None:
            return
        node = self.engine.nodes[p.node_id]
        t = node.trust
        if passed:
            t.challenge_passed(p.type)
        elif p.type == "identity":
            t.identity_failed()
        else:
            t.integrity_failed()
        # firmware attestation bookkeeping + the silent/sleeper-compromise verdict
        if p.type == "integrity":
            node.last_attested = time.time()
            node.fw_ok = passed
            node.fw_detail = detail
            if not passed:
                data_normal = (t.identity >= 99 and t.consistency >= 99
                               and not any(n > 0 for n in node.disagree_cycles.values()))
                node.silent_compromise = data_normal
                if data_normal:
                    slp_id = f"slp-{uuid.uuid4().hex[:6]}"
                    summary = (f"SLEEPER COMPROMISE: {p.node_id} firmware fingerprint tampered while its data stayed "
                               f"nominal - caught by attestation, not by data anomaly")
                    self.engine.bus.publish({"e": "sleeper_detected", "node_id": p.node_id, "detail": detail})
                    self.engine.bus.publish({"e": "incident", "id": slp_id, "node_id": p.node_id, "claim": "integrity", "summary": summary})
                    self.engine.store.add_incident(slp_id, "integrity", summary,
                                                   {"detail": detail, "silent": True, "data_state": "nominal"})
            else:
                node.silent_compromise = False
        self.engine.store.close_challenge(cid, passed, detail)
        from .engine import LED_CODE  # restore the state LEDs after the challenge blink
        await self.engine.transport.send(p.node_id, {"t": "led", "code": LED_CODE.get(t.derive_state(), 0)})
        node.last_reason = f"{p.type} challenge {'passed' if passed else 'failed'}: {detail}"
        self.engine.bus.publish({"e": "challenge_result", "node_id": p.node_id, "challenge_id": cid,
                                 "type": p.type, "passed": passed, "detail": detail,
                                 "recovery": t.recovery_label})
        self.engine.apply_state(node, node.last_reason)
        self.engine.publish_node(node, force=True)
