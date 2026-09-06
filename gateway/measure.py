"""Measure ARES in simulation and write metrics.json for the /metrics endpoint.

    python measure.py --trials 20 --honest 120

For each trial: person present, SUPPRESS MOTION on A, measure
  t_suspicious  first state change away from TRUSTED
  t_shadow      A reaches SHADOW (challenge failed)
  caught        motion stayed CONFIRMED by the other two witnesses throughout
then RESTORE and wait for A to be TRUSTED again.

Then an honest run of --honest seconds with nobody attacking: any non-TRUSTED state on
any witness is a false positive."""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

from ares.app import create_app


async def wait_state(eng, node, states, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if eng.nodes[node].trust.state in states:
            return time.time() - t0
        await asyncio.sleep(0.05)
    return None


async def run(trials: int, honest: int, interval: float) -> dict:
    app = create_app(mode="sim", db_path=":memory:", sim_interval=interval,
                     suspicious_retry=1.0, shadow_retry=2.0, recovery_retry=0.5)
    eng, tr, bus = app.state.engine, app.state.transport, app.state.bus
    await tr.start(asyncio.get_running_loop())
    await eng.start()
    tr.set_env(person=True)
    await asyncio.sleep(3)

    t_susp, t_shadow, caught = [], [], 0
    for i in range(trials):
        await eng.attack("suppress_motion", "A")
        t0 = time.time()
        a = await wait_state(eng, "A", ("SUSPICIOUS", "SHADOW"), 15)
        b = await wait_state(eng, "A", ("SHADOW",), 15)
        confirmed = eng.claims["motion"]["status"] == "CONFIRMED" and "A" in eng.claims["motion"]["against"]
        if a is not None:
            t_susp.append(a)
        if b is not None:
            t_shadow.append(a + b if a is not None else b)
        caught += 1 if (b is not None and confirmed) else 0
        await eng.attack("restore", "A")
        await wait_state(eng, "A", ("TRUSTED",), 30)
        await asyncio.sleep(1.0)
        print(f"trial {i + 1:2d}: suspicious {a and round(a, 2)} s, shadow {b is not None and round(a + b, 2)} s, "
              f"confirmed by others: {confirmed}")

    # honest run
    tr.set_env(person=False)
    await asyncio.sleep(2)
    false_pos, t0, worst = 0, time.time(), {}
    while time.time() - t0 < honest:
        tr.set_env(person=(int(time.time()) // 7) % 2 == 0)   # people come and go
        for n, rec in eng.nodes.items():
            if rec.trust.state != "TRUSTED":
                false_pos += 1
                worst[n] = rec.last_reason
        await asyncio.sleep(1.0)
    await eng.stop()
    await tr.stop()

    def pct(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))] if xs else None

    return {
        "trials": trials,
        "sim_interval_s": interval,
        "detection_latency_s": {
            "to_suspicious_median": round(statistics.median(t_susp), 2) if t_susp else None,
            "to_shadow_median": round(statistics.median(t_shadow), 2) if t_shadow else None,
            "to_shadow_p95": round(pct(t_shadow, 0.95), 2) if t_shadow else None,
        },
        "catch_rate": round(caught / trials, 3) if trials else None,
        "honest_run_s": honest,
        "false_positive_seconds": false_pos,
        "false_positive_rate_per_hour": round(false_pos * 3600 / honest, 2) if honest else None,
        "false_positive_reasons": worst,
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--honest", type=int, default=120, help="seconds of honest operation to watch")
    ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--out", default="metrics.json")
    args = ap.parse_args()
    result = asyncio.run(run(args.trials, args.honest, args.interval))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
