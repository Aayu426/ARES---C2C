"""The ARES engine.

Phase 1: ingest, verify signatures, normalise everything into witnesses, persist,
broadcast.  Phase 2: trust vector with debt, claim consistency across witnesses,
physics rules, state machine.  Phase 3 (next): challenges, shadow decisions, consensus
actions.

Everything the engine sees is a *witness*: node A's `motion: 1` and camera C's
`{claim: motion, value: 1}` become the same shape. That is the whole design."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid

from .bus import EventBus
from .challenges import ChallengeEngine
from .canonical import new_key_hex, telemetry_canonical, verify, witness_canonical
from .physics import Physics
from .store import Store
from .transports.base import Transport
from .trust import TrustVector

NODE_IDS = ["A", "B", "C", "WEBCAM"]
CLAIMS_OF = {"A": ["motion", "temp"], "B": ["water"], "C": ["motion", "water"], "WEBCAM": ["motion", "water"]}
VOTED_CLAIMS = ("motion", "water")     # claims with several witnesses
FRESH_SECONDS = 3.0                    # a reading older than this does not vote
MIN_VISION_CONF = 0.6
OUTLIER_GRACE_CYCLES = 1               # first disagreeing cycle is free (sensor latency)
TICK_SECONDS = 1.0
CONFLICT_RETRY = 5.0                   # seconds between tie-break challenges per node
LED_CODE = {"TRUSTED": 0, "SUSPICIOUS": 1, "RECOVERING": 1, "SHADOW": 2}   # status LEDs on the boards


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
        self.trust = TrustVector()
        self.last_seen: float | None = None
        self.last_seq: int | None = None
        self.last_ts: float | None = None
        self.last_conflict_challenge = 0.0
        self.last: dict = {}                       # last raw values shown on the dashboard
        self.latest: dict[str, tuple[float, float, float]] = {}   # claim -> (value, conf, at) accepted readings
        self.disagree_cycles: dict[str, int] = {}  # claim -> consecutive cycles as outlier
        self.hmac_failures = 0
        self.frames = 0
        self.good_this_tick = 0
        self.bad_this_tick = 0
        self.last_reason = ""

    @property
    def online(self) -> bool:
        return self.last_seen is not None and (time.time() - self.last_seen) < 5.0

    def snapshot(self) -> dict:
        t = self.trust
        return {
            "e": "node_update", "node_id": self.node_id, "state": t.state,
            "identity": round(t.identity), "integrity": round(t.integrity),
            "consistency": round(t.consistency), "overall": t.overall,
            "recovery": t.recovery_label, "last": dict(self.last),
            "last_seen": self.last_seen, "online": self.online, "reason": self.last_reason,
        }


class Engine:
    def __init__(self, transport: Transport, store: Store, bus: EventBus, keys: dict[str, bytes], mode: str,
                 known_fw: dict[str, str] | None = None, **challenge_opts) -> None:
        self.transport = transport
        self.store = store
        self.bus = bus
        self.keys = keys
        self.mode = mode
        self.physics = Physics()
        self.nodes: dict[str, NodeRecord] = {n: NodeRecord(n) for n in NODE_IDS}
        self.claims: dict[str, dict] = {c: {"status": "CLEAR", "by": [], "against": [], "value": 0} for c in VOTED_CLAIMS}
        self.alarm = {"on": False, "reason": "baseline"}
        self._tick_task: asyncio.Task | None = None
        self._last_snapshot: dict[str, str] = {}
        self._incident_n = 0
        self.mqtt_echo = None   # set by MqttIngress when --mqtt-echo is on
        self.challenges = ChallengeEngine(self, known_fw or {}, **challenge_opts)
        transport.on_message(self.on_message)

    # ---- lifecycle ----

    async def start(self) -> None:
        self._tick_task = asyncio.create_task(self._tick_loop())
        await self.challenges.start()

    async def stop(self) -> None:
        await self.challenges.stop()
        if self._tick_task:
            self._tick_task.cancel()

    # ---- inbound ----

    async def on_message(self, msg: dict, source: str) -> None:
        kind = msg.get("t")
        node_id = msg.get("node_id")
        if node_id not in self.nodes:
            return
        node = self.nodes[node_id]
        if kind == "tel":
            await self._on_telemetry(node, msg, source)
        elif kind == "wit":
            await self._on_witness_msg(node, msg, source)
        elif kind == "resp":
            await self.on_challenge_response(node, msg)   # Phase 3

    async def _on_telemetry(self, node: NodeRecord, msg: dict, source: str = "") -> None:
        ok = verify(self.keys[node.node_id], telemetry_canonical(msg), msg.get("hmac"))
        replay = ok and self._is_replay(node, msg)
        self._touch(node, msg, ok and not replay)
        self.store.add_telemetry(msg, ok and not replay)
        if not ok:
            self._identity_failure(node, "invalid signature on telemetry frame", msg, source)
            return
        if replay:
            self._replay_failure(node, msg)
            return
        for claim in ("motion", "water", "temp"):
            if claim in msg:
                node.last[claim] = msg[claim]
                await self.on_witness(node, claim, float(msg[claim]), 1.0, ok)
        if self.mqtt_echo is not None and str(msg.get("hmac")) != "":
            self.mqtt_echo(msg)   # let a network attacker sniff genuine signed frames (echo mode)
        self._publish_node(node)

    async def _on_witness_msg(self, node: NodeRecord, msg: dict, source: str = "") -> None:
        ok = verify(self.keys[node.node_id], witness_canonical(msg), msg.get("hmac"))
        replay = ok and self._is_replay(node, msg)
        self._touch(node, msg, ok and not replay)
        if not ok:
            self._identity_failure(node, "invalid signature on witness message", msg, source)
            return
        if replay:
            self._replay_failure(node, msg)
            return
        claim = msg.get("claim")
        if claim not in VOTED_CLAIMS:
            return
        node.last[claim] = int(msg.get("value", 0))
        await self.on_witness(node, claim, float(msg.get("value", 0)), float(msg.get("conf", 1.0)), ok)
        self._publish_node(node)

    def _is_replay(self, node: NodeRecord, msg: dict) -> bool:
        """Sequence must advance. A reboot (seq restarts near 1 with a small millis clock)
        is allowed; anything else that goes backwards is a captured frame re-sent."""
        seq, ts = msg.get("seq"), msg.get("ts")
        if not isinstance(seq, int) or node.last_seq is None:
            return False
        if seq > node.last_seq:
            return False
        rebooted = seq <= 3 and isinstance(ts, (int, float)) and isinstance(node.last_ts, (int, float)) and ts < node.last_ts
        return not rebooted

    def _replay_failure(self, node: NodeRecord, msg: dict) -> None:
        node.trust.replayed()
        node.last_reason = f"replayed frame rejected: seq {msg.get('seq')} already seen (last {node.last_seq})"
        self.bus.publish({"e": "replay_rejected", "node_id": node.node_id, "seq": msg.get("seq"), "detail": node.last_reason})
        self.bus.publish({"e": "incident", "id": f"rep-{uuid.uuid4().hex[:6]}", "claim": "identity",
                          "summary": f"{node.node_id}: {node.last_reason}"})
        self._apply_state(node, node.last_reason)
        self._publish_node(node, force=True)

    def _touch(self, node: NodeRecord, msg: dict, ok: bool) -> None:
        node.last_seen = time.time()
        node.frames += 1
        seq, ts = msg.get("seq"), msg.get("ts")
        if ok and isinstance(seq, int):
            node.last_seq = seq
            node.last_ts = ts if isinstance(ts, (int, float)) else node.last_ts
        if ok:
            node.good_this_tick += 1
        else:
            node.hmac_failures += 1
            node.bad_this_tick += 1

    def _identity_failure(self, node: NodeRecord, detail: str, msg: dict | None = None, source: str = "") -> None:
        node.trust.bad_hmac()
        attacker = source.startswith("mqtt-attacker") or source == "attacker"
        where = " over the network" if attacker else ""
        node.last_reason = f"{detail}{where}"
        # surface the value the forged frame TRIED to push, so the dashboard shows a
        # rejected ghost reading next to the real one. The real reading is never overwritten.
        attempted = {}
        if msg:
            for claim in ("motion", "water", "temp"):
                if claim in msg:
                    attempted[claim] = msg[claim]
            if msg.get("claim") in ("motion", "water"):
                attempted[msg["claim"]] = msg.get("value")
        self.bus.publish({"e": "identity_failure", "node_id": node.node_id, "detail": node.last_reason,
                          "attempted": attempted, "source": source or "serial"})
        for claim, value in attempted.items():
            self.bus.publish({"e": "witness", "node_id": node.node_id, "claim": claim,
                              "value": value, "conf": 1.0, "rejected": "forged signature", "source": source or "serial"})
        self._apply_state(node, node.last_reason)
        self._publish_node(node, force=True)

    async def on_witness(self, node: NodeRecord, claim: str, value: float, conf: float, hmac_ok: bool) -> None:
        """Every reading, real or simulated, sensor or camera, lands here as a witness."""
        violation = self.physics.check(node.node_id, claim, value)
        self.store.add_witness(node.node_id, claim, value, conf, hmac_ok)
        event = {"e": "witness", "node_id": node.node_id, "claim": claim, "value": value, "conf": conf}
        if violation:
            node.trust.physics_violation()
            node.last_reason = f"physics: {violation}"
            event["rejected"] = violation
            self.bus.publish(event)
            self.bus.publish({"e": "incident", "id": f"phy-{uuid.uuid4().hex[:6]}", "claim": claim,
                              "summary": f"{node.node_id} reading {value} rejected: {violation}; no action taken"})
            self._apply_state(node, node.last_reason)
            return
        node.latest[claim] = (value, conf, time.time())
        self.bus.publish(event)
        if claim == "temp":
            drift = self.physics.check_drift(node.node_id, claim, value)
            if drift:
                node.trust.outlier()            # a patient liar bleeds trust the same way an outlier does
                node.trust.outlier()
                node.last_reason = drift
                self.bus.publish({"e": "drift_detected", "node_id": node.node_id, "claim": claim, "detail": drift})
                self.bus.publish({"e": "incident", "id": f"drf-{uuid.uuid4().hex[:6]}", "claim": claim,
                                  "summary": f"{node.node_id}: {drift}"})
                self._apply_state(node, drift)
                self._publish_node(node, force=True)

    async def on_challenge_response(self, node: NodeRecord, msg: dict) -> None:
        await self.challenges.on_response(node, msg)

    # ---- the 1 s consistency tick ----

    async def _tick_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(TICK_SECONDS)
                try:
                    self._tick()
                except Exception as exc:  # never let the tick die
                    import traceback
                    print(f"[engine] tick error: {exc!r}", flush=True)
                    traceback.print_exc()
        except asyncio.CancelledError:
            pass

    def _tick(self) -> None:
        now = time.time()
        outliers: set[str] = set()
        for claim in VOTED_CLAIMS:
            votes: dict[str, float] = {}
            reporters: dict[str, float] = {}
            for node in self.nodes.values():
                if claim not in node.latest:
                    continue
                value, conf, at = node.latest[claim]
                if now - at > FRESH_SECONDS or conf < MIN_VISION_CONF:
                    continue
                reporters[node.node_id] = value
                if node.trust.voting:
                    votes[node.node_id] = value

            # only witnesses that can still be believed take part in a disagreement
            active = {n: v for n, v in reporters.items() if self.nodes[n].trust.state in ("TRUSTED", "SUSPICIOUS")}
            majority = self._majority(votes)
            disagreement = len(set(active.values())) > 1

            if majority is None or (len(votes) < 2 and disagreement):
                # no majority, or a lone voter facing dissent: a tie. Proof decides, not the vote.
                status = "UNKNOWN" if disagreement else ("CONFIRMED" if majority == 1 else "CLEAR")
                by = [n for n, v in votes.items() if majority is not None and v == majority] if not disagreement else []
                self._set_claim(claim, status, by, [n for n in active if n not in by], int(majority or 0))
                if status == "UNKNOWN":
                    self._challenge_conflict(claim, list(active))
                continue

            by = [n for n, v in votes.items() if v == majority]
            against = [n for n, v in reporters.items() if v != majority]
            for node_id in against:
                outliers.add(node_id)
                node = self.nodes[node_id]
                node.disagree_cycles[claim] = node.disagree_cycles.get(claim, 0) + 1
                if node.disagree_cycles[claim] > OUTLIER_GRACE_CYCLES and not node.trust.verified_recently():
                    node.trust.outlier()
                    node.last_reason = (f"outlier on {claim} for {node.disagree_cycles[claim]} cycles: "
                                        f"{', '.join(by)} report {int(majority)}, {node_id} reports {int(reporters[node_id])}")
            for node_id in by:
                self.nodes[node_id].disagree_cycles[claim] = 0
            self._set_claim(claim, "CONFIRMED" if majority == 1 else "CLEAR", by, against, int(majority))

        for node in self.nodes.values():
            clean = node.node_id not in outliers and node.good_this_tick > 0 and node.bad_this_tick == 0
            if clean:
                node.trust.clean_cycle()
            node.good_this_tick = node.bad_this_tick = 0
            self._apply_state(node, node.last_reason)
            self._publish_node(node)

    def _challenge_conflict(self, claim: str, reporters: list[str]) -> None:
        """No majority (for example 1 vs 1): proof breaks the tie. Every conflicting
        witness is asked for its firmware fingerprint; a failure shadows it and the
        remaining witnesses form the majority."""
        now = time.time()
        for node_id in reporters:
            node = self.nodes[node_id]
            if node.trust.state not in ("TRUSTED", "SUSPICIOUS"):
                continue
            if any(p.node_id == node_id for p in self.challenges.pending.values()):
                continue
            if now - node.last_conflict_challenge < CONFLICT_RETRY:
                continue
            node.last_conflict_challenge = now
            others = ", ".join(n for n in reporters if n != node_id)
            reason = f"{claim}: {node_id} and {others} disagree with no majority -> asking {node_id} to prove its firmware"
            asyncio.ensure_future(self.challenges.issue(node, "integrity", reason))

    @staticmethod
    def _majority(votes: dict[str, float]) -> float | None:
        if not votes:
            return None
        counts: dict[float, int] = {}
        for v in votes.values():
            counts[v] = counts.get(v, 0) + 1
        best, n = max(counts.items(), key=lambda kv: kv[1])
        return best if n * 2 > len(votes) else None

    def _set_claim(self, claim: str, status: str, by: list[str], against: list[str], value: int) -> None:
        prev = self.claims[claim]
        new = {"status": status, "by": sorted(by), "against": sorted(against), "value": value}
        if new != prev:
            self.claims[claim] = new
            self.bus.publish({"e": "claim", "claim": claim, **new})
            if status == "UNKNOWN":
                self.bus.publish({"e": "conflict", "claim": claim, "witnesses": {n: int(self.nodes[n].latest[claim][0]) for n in against}, "status": "UNKNOWN"})
                self.bus.publish({"e": "escalation", "node_id": None, "claim": claim,
                                  "reason": f"{claim}: witnesses conflict with no majority -> no action, human decision"})
            new_liars = set(against) - set(prev.get("against", []))
            asyncio.ensure_future(self._update_alarm())   # never downstream of a database write
            if status == "CONFIRMED" and (prev.get("status") != "CONFIRMED" or new_liars):
                self._incident_n += 1
                iid = f"i-{uuid.uuid4().hex[:6]}"          # unique across gateway restarts
                liars = ", ".join(against) if against else "nobody"
                summary = f"{claim} confirmed by {', '.join(by)}; {liars} reported none"
                evidence = {"claim": claim, "by": by, "against": against,
                            "states": {n: self.nodes[n].trust.state for n in by + against},
                            "reasons": {n: f"it reported no {claim} while {', '.join(by)} reported {claim}" for n in against},
                            "node_status": {n: self.nodes[n].last_reason for n in against}}
                try:
                    self.store.add_incident(iid, claim, summary, evidence)
                except Exception as exc:
                    print(f"[engine] incident store failed: {exc!r}", flush=True)
                self.bus.publish({"e": "incident", "id": iid, "claim": claim, "summary": summary, "evidence": evidence})

    async def _update_alarm(self) -> None:
        confirmed = [c for c, v in self.claims.items() if v["status"] == "CONFIRMED"]
        on = bool(confirmed)
        reason = ("; ".join(f"{c} confirmed by {', '.join(self.claims[c]['by'])}" for c in confirmed)
                  if on else "all claims clear")
        if on != self.alarm["on"] or (on and reason != self.alarm["reason"]):
            self.alarm = {"on": on, "reason": reason}
            self.bus.publish({"e": "alarm", "on": on, "reason": reason})
            await self.transport.send("A", {"t": "alarm", "on": 1 if on else 0, "reason": reason})

    def _apply_state(self, node: NodeRecord, reason: str) -> None:
        change = node.trust.update_state()
        if change:
            old, new = change
            self.bus.publish({"e": "state_change", "node_id": node.node_id, "from": old, "to": new, "reason": reason})
            t = node.trust
            self.store.add_trust(node.node_id, t.identity, t.integrity, t.consistency, t.overall, new)
            asyncio.ensure_future(self.on_state_change(node, old, new, reason))

    async def on_state_change(self, node: NodeRecord, old: str, new: str, reason: str) -> None:
        """SUSPICIOUS: challenge immediately, the scheduler handles SHADOW and RECOVERING re-tests."""
        await self.transport.send(node.node_id, {"t": "led", "code": LED_CODE.get(new, 0)})
        if new == "SUSPICIOUS" and not any(p.node_id == node.node_id for p in self.challenges.pending.values()):
            choice = self.challenges.pick(node)
            if choice:
                await self.challenges.issue(node, *choice)

    def apply_state(self, node: NodeRecord, reason: str) -> None:
        self._apply_state(node, reason)

    def publish_node(self, node: NodeRecord, force: bool = False) -> None:
        self._publish_node(node, force)

    def _publish_node(self, node: NodeRecord, force: bool = False) -> None:
        # A node that has never reported (e.g. a camera that is not deployed) is not
        # broadcast, so the dashboard shows only witnesses that actually exist. It
        # appears the moment it sends its first frame.
        if node.last_seen is None and not force:
            return
        snap = node.snapshot()
        key = json.dumps({k: snap[k] for k in ("state", "identity", "integrity", "consistency", "recovery", "last", "online")}, sort_keys=True, default=str)
        if force or self._last_snapshot.get(node.node_id) != key:
            self._last_snapshot[node.node_id] = key
            self.bus.publish(snap)

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
                if n.trust.state in ("SHADOW", "SUSPICIOUS"):
                    n.trust.start_recovery()
                    n.last_reason = "restored: must pass 10 consecutive challenges before voting"
                    self._apply_state(n, n.last_reason)
                    self._publish_node(n, force=True)
            reached = [n for n in self.nodes if await self.transport.send(n, msg)]
            return f"restore sent to {', '.join(reached) or 'nobody'}"
        if mode in ("spoof", "replay") and self.mode != "sim":
            # real boards cannot impersonate themselves: the gateway plays the attacker
            return await self._inject_attack(mode, node_id)
        sent = await self.transport.send(node_id, msg)
        return f"{mode} sent to {node_id}" if sent else f"{node_id} unreachable"

    async def _inject_attack(self, mode: str, node_id: str) -> str:
        node = self.nodes[node_id]
        if mode == "spoof":
            for i in range(3):
                seq = (node.last_seq or 0) + 1 + i
                forged = {"t": "tel", "node_id": node_id, "seq": seq, "ts": int(time.time() * 1000)}
                forged.update({"motion": 1} if node_id == "A" else {"water": 1})
                forged["hmac"] = "0" * 64
                await self.on_message(forged, "attacker")
            return f"3 forged frames injected as {node_id} without its key"
        frames = self.store.recent_telemetry(node_id, 5)
        if not frames:
            return f"no captured frames for {node_id} yet"
        for f in frames:
            await self.on_message(dict(f), "attacker")
        return f"{len(frames)} captured frames replayed as {node_id}"

    def state(self) -> dict:
        return {"mode": self.mode,
                "nodes": {n: r.snapshot() for n, r in self.nodes.items() if r.last_seen is not None},
                "claims": self.claims, "alarm": self.alarm,
                "incidents": self.store.recent_incidents(20), "time": time.time()}
