"""Physics plausibility rules, CONTRACTS.md section 5.

A reading that the world could not have produced is rejected before it reaches
consensus, and the reporting witness takes consistency debt. Physics can block an
action on its own; it never dismisses a corroborated claim."""
from __future__ import annotations

import time
from collections import deque

TEMP_MAX_RATE = 2.0        # °C per second
TEMP_MIN, TEMP_MAX = 5.0, 60.0
ZERO_VAR_WINDOW = 120.0    # seconds
ZERO_VAR_SAMPLES = 30
ZERO_VAR_EPS = 0.01
FLAP_MAX_PER_SEC = 5


class ClaimHistory:
    """Per (node, claim) history of (time, value)."""

    def __init__(self) -> None:
        self.samples: deque[tuple[float, float]] = deque(maxlen=400)
        self.transitions: deque[float] = deque(maxlen=64)
        self.last_zero_var_penalty: float = 0.0

    def push(self, value: float, at: float | None = None) -> None:
        at = at or time.time()
        if self.samples and self.samples[-1][1] != value:
            self.transitions.append(at)
        self.samples.append((at, value))


class Physics:
    def __init__(self) -> None:
        self.hist: dict[tuple[str, str], ClaimHistory] = {}

    def _h(self, node_id: str, claim: str) -> ClaimHistory:
        return self.hist.setdefault((node_id, claim), ClaimHistory())

    def check(self, node_id: str, claim: str, value: float) -> str | None:
        """Return a violation reason, or None if the reading is plausible.
        The reading is recorded either way so the next check has context."""
        h = self._h(node_id, claim)
        now = time.time()
        reason = None

        if claim == "temp":
            if value < TEMP_MIN or value > TEMP_MAX:
                reason = f"{value:.1f} °C is outside the indoor range {TEMP_MIN:.0f}–{TEMP_MAX:.0f} °C"
            elif h.samples:
                t0, v0 = h.samples[-1]
                dt = max(now - t0, 1e-3)
                rate = abs(value - v0) / dt
                if rate > TEMP_MAX_RATE and abs(value - v0) > 1.0:
                    reason = f"{abs(value - v0):.1f} °C change in {dt:.1f} s violates physics"
            if reason is None:
                recent = [v for (t, v) in h.samples if now - t <= ZERO_VAR_WINDOW]
                if (len(recent) >= ZERO_VAR_SAMPLES and max(recent) - min(recent) < ZERO_VAR_EPS
                        and now - h.last_zero_var_penalty > ZERO_VAR_WINDOW):
                    h.last_zero_var_penalty = now
                    reason = f"identical to {ZERO_VAR_EPS} °C for {ZERO_VAR_WINDOW:.0f} s: a real sensor has noise"

        elif claim in ("motion", "water"):
            h.push(value, now)
            recent = [t for t in h.transitions if now - t <= 1.0]
            if len(recent) > FLAP_MAX_PER_SEC:
                return f"{claim} flapped {len(recent)} times in 1 s"
            return None

        h.push(value, now)
        return reason
