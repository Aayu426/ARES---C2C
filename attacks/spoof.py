"""Spoof attack: pretend to be a node without its key.

An attacker who can reach the gateway (here: its HTTP inbox, the same door the vision
service uses) sends frames claiming to be node A with a forged signature. ARES rejects
them on the first frame and puts A's identity at 0.

    python spoof.py --gateway http://127.0.0.1:8000 --node A --frames 3
"""
from __future__ import annotations

import argparse
import time

import requests


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", default="http://127.0.0.1:8000")
    ap.add_argument("--node", default="A")
    ap.add_argument("--frames", type=int, default=3)
    args = ap.parse_args()

    seq = 900000
    for i in range(args.frames):
        seq += 1
        frame = {"t": "tel", "node_id": args.node, "seq": seq, "ts": int(time.time() * 1000)}
        frame.update({"motion": 1} if args.node == "A" else {"water": 1})
        frame["hmac"] = "deadbeef" * 8   # no key, no valid signature
        r = requests.post(f"{args.gateway}/inbox", json=frame, timeout=3)
        print(f"sent forged frame {i + 1} as {args.node}: HTTP {r.status_code}")
        time.sleep(0.5)

    state = requests.get(f"{args.gateway}/state", timeout=3).json()
    n = state["nodes"][args.node]
    print(f"{args.node} now: state={n['state']} identity={n['identity']} reason={n.get('reason')!r}")


if __name__ == "__main__":
    main()
