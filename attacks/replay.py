"""Replay attack: capture a node's real, validly signed frames and send them again.

The signatures are genuine, so signature checking alone would accept them. ARES rejects
them because the sequence number has already been seen: seq must always advance, and
only a reboot (seq restarting near 1 with a reset millis clock) is allowed to go back.

    python replay.py --gateway http://127.0.0.1:8000 --node A --frames 5
"""
from __future__ import annotations

import argparse
import time

import requests


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", default="http://127.0.0.1:8000")
    ap.add_argument("--node", default="A")
    ap.add_argument("--frames", type=int, default=5)
    args = ap.parse_args()

    captured = requests.get(f"{args.gateway}/capture/{args.node}", params={"n": args.frames}, timeout=3).json()
    if not captured:
        raise SystemExit(f"nothing captured for {args.node}; is it reporting?")
    print(f"captured {len(captured)} genuine frames from {args.node} (seq {captured[0]['seq']}..{captured[-1]['seq']})")
    time.sleep(1.0)
    for f in captured:
        r = requests.post(f"{args.gateway}/inbox", json=f, timeout=3)
        print(f"replayed seq {f['seq']}: HTTP {r.status_code}")
        time.sleep(0.3)

    state = requests.get(f"{args.gateway}/state", timeout=3).json()
    n = state["nodes"][args.node]
    print(f"{args.node} now: state={n['state']} identity={n['identity']} reason={n.get('reason')!r}")


if __name__ == "__main__":
    main()
