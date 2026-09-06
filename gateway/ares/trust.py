"""Trust vector with trust debt. CONTRACTS.md section 4.

Each component is `100 - debt`. Debt is added by evidence against the node and repaid
slowly by clean behaviour. Nothing resets instantly; recovery is earned."""
from __future__ import annotations

import time

WEIGHTS = {"identity": 0.35, "integrity": 0.35, "consistency": 0.30}

# debt table
DEBT_BAD_HMAC = 100
DEBT_IDENTITY_FAIL = 100
DEBT_INTEGRITY_FAIL = 100
DEBT_OUTLIER = 30
DEBT_PHYSICS = 40
REPAY_CLEAN = 2
REPAY_CHALLENGE = 20

# state thresholds
TRUSTED_MIN = 70
SHADOW_MAX = 40
COMPONENT_FLOOR = 50          # any component below this → SUSPICIOUS
FAILED_CHALLENGE_WINDOW = 60  # seconds a failed challenge keeps a node in SHADOW
RECOVERY_PASSES = 10          # consecutive passed challenges before the vote counts


class TrustVector:
    def __init__(self) -> None:
        self.debt = {"identity": 0.0, "integrity": 0.0, "consistency": 0.0}
        self.last_failed_challenge: float | None = None
        self.recovering = False
        self.recovery_passed = 0
        self.state = "TRUSTED"
        self.state_since = time.time()

    # ---- components ----

    def component(self, name: str) -> float:
        return max(0.0, min(100.0, 100.0 - self.debt[name]))

    @property
    def identity(self) -> float:
        return self.component("identity")

    @property
    def integrity(self) -> float:
        return self.component("integrity")

    @property
    def consistency(self) -> float:
        return self.component("consistency")

    @property
    def overall(self) -> float:
        return round(sum(WEIGHTS[k] * self.component(k) for k in WEIGHTS), 1)

    def _add(self, name: str, amount: float) -> None:
        self.debt[name] = max(0.0, min(100.0, self.debt[name] + amount))

    # ---- evidence against ----

    def _hard_failure(self) -> None:
        # any hard failure ends a recovery in progress: restore must be pressed again
        self.last_failed_challenge = time.time()
        self.recovery_passed = 0
        self.recovering = False

    def bad_hmac(self) -> None:
        self._add("identity", DEBT_BAD_HMAC)
        self._hard_failure()   # an impostor stays in SHADOW like a failed challenge

    def replayed(self) -> None:
        """A captured frame re-sent later: same debt and shadow lock as a bad signature."""
        self.bad_hmac()

    def identity_failed(self) -> None:
        self._add("identity", DEBT_IDENTITY_FAIL)
        self._hard_failure()

    def integrity_failed(self) -> None:
        self._add("integrity", DEBT_INTEGRITY_FAIL)
        self._hard_failure()

    def outlier(self) -> None:
        self._add("consistency", DEBT_OUTLIER)

    def physics_violation(self) -> None:
        self._add("consistency", DEBT_PHYSICS)

    # ---- evidence for ----

    def clean_cycle(self) -> None:
        for k in self.debt:
            self._add(k, -REPAY_CLEAN)

    def challenge_passed(self, component: str) -> None:
        self._add(component, -REPAY_CHALLENGE)
        if self.recovering:
            for k in self.debt:                     # earning the vote back repays every component
                self._add(k, -REPAY_CHALLENGE / 2)
            self.recovery_passed += 1
            if self.recovery_passed >= RECOVERY_PASSES:
                self.recovering = False
                self.last_failed_challenge = None

    def start_recovery(self) -> None:
        """Called on restore: the node must earn its vote back."""
        self.recovering = True
        self.recovery_passed = 0
        # the failed-challenge lock is lifted so challenges can start counting,
        # but the debt stays and is repaid one passed challenge at a time
        self.last_failed_challenge = None

    # ---- state ----

    @property
    def recovery_label(self) -> str | None:
        return f"{self.recovery_passed}/{RECOVERY_PASSES}" if self.recovering else None

    @property
    def voting(self) -> bool:
        return self.state == "TRUSTED"

    def derive_state(self) -> str:
        now = time.time()
        recently_failed = (self.last_failed_challenge is not None
                           and now - self.last_failed_challenge < FAILED_CHALLENGE_WINDOW)
        if self.recovering:
            return "RECOVERING"
        if recently_failed or self.overall < SHADOW_MAX or self.identity == 0 or self.integrity == 0:
            return "SHADOW"
        if self.overall < TRUSTED_MIN or min(self.identity, self.integrity, self.consistency) < COMPONENT_FLOOR:
            return "SUSPICIOUS"
        return "TRUSTED"

    def update_state(self) -> tuple[str, str] | None:
        """Recompute; returns (old, new) when the state changed."""
        new = self.derive_state()
        if new != self.state:
            old, self.state, self.state_since = self.state, new, time.time()
            return old, new
        return None
