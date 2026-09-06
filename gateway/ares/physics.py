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

# slow drift: every step passes the rate rule, but the short-term level walks away
# from the long-term baseline in one direction
DRIFT_BASELINE_ALPHA = 0.02     # long memory (~50 samples)
DRIFT_SHORT_ALPHA = 0.3         # short memory (~3 samples)
DRIFT_MIN_SAMPLES = 15
DRIFT_THRESHOLD = 1.5           # °C short-term above/below baseline
DRIFT_ONE_SIDED = 0.8           # fraction of recent steps that must share a sign
DRIFT_COOLDOWN = 5.0            # seconds between penalties for the same sensor


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


class DriftTracker:
    def __init__(self) -> None:
        self.baseline: float | None = None
        self.short: float | None = None
        self.n = 0
        self.steps: deque[float] = deque(maxlen=20)
        self.last_value: float | None = None
        self.last_penalty = 0.0
        self.started_at: float | None = None

    def update(self, value: float) -> str | None:
        now = time.time()
        if self.baseline is None:
            self.baseline = self.short = value
            self.started_at = now
        else:
            self.steps.append(value - (self.last_value if self.last_value is not None else value))
            self.short = DRIFT_SHORT_ALPHA * value + (1 - DRIFT_SHORT_ALPHA) * self.short
            self.baseline = DRIFT_BASELINE_ALPHA * value + (1 - DRIFT_BASELINE_ALPHA) * self.baseline
        self.last_value = value
        self.n += 1
        if self.n < DRIFT_MIN_SAMPLES or len(self.steps) < 8:
            return None
        gap = self.short - self.baseline
        signs = [1 if s > 0 else -1 if s < 0 else 0 for s in self.steps]
        pos = sum(1 for s in signs if s > 0) / len(signs)
        neg = sum(1 for s in signs if s < 0) / len(signs)
        one_sided = max(pos, neg) >= DRIFT_ONE_SIDED
        if abs(gap) >= DRIFT_THRESHOLD and one_sided and now - self.last_penalty > DRIFT_COOLDOWN:
            self.last_penalty = now
            biggest = max(abs(s) for s in self.steps)
            return (f"slow drift: {gap:+.1f} °C from baseline in steps of at most {biggest:.2f} °C, "
                    f"each too small for any alarm")
        return None


class Physics:
    def __init__(self) -> None:
        self.hist: dict[tuple[str, str], ClaimHistory] = {}
        self.drift: dict[tuple[str, str], DriftTracker] = {}

    def check_drift(self, node_id: str, claim: str, value: float) -> str | None:
        return self.drift.setdefault((node_id, claim), DriftTracker()).update(value)

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
