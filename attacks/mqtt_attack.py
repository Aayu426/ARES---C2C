"""MQTT attacker, run from another PC on the same hotspot.

The gateway subscribes to `ares/inject/<node>` on the broker. Anything published there is
fed to ARES as if it came from that node.

    # impersonate node A with no key (forged signature)
    python mqtt_attack.py --broker 10.212.204.125 --node A --mode spoof

    # replay: capture a genuine signed frame (needs the gateway started with --mqtt-echo)
    # then send it back so its sequence number is stale
    python mqtt_attack.py --broker 10.212.204.125 --node A --mode replay

Only needs paho-mqtt (`pip install paho-mqtt`). Or use the mosquitto CLI directly:
    mosquitto_pub -h 10.212.204.125 -t ares/inject/A -m "{\"seq\":9999,\"motion\":1,\"hmac\":\"bad\"}"
"""
from __future__ import annotations

import argparse
import json
import time

import paho.mqtt.client as mqtt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", required=True, help="broker IP (the PC running Mosquitto)")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--node", default="A")
    ap.add_argument("--mode", choices=["spoof", "replay"], default="spoof")
    ap.add_argument("--frames", type=int, default=3)
    args = ap.parse_args()

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ares-attacker")
    c.connect(args.broker, args.port); c.loop_start()
    inject = f"ares/inject/{args.node}"

    if args.mode == "spoof":
        for i in range(args.frames):
            frame = {"node_id": args.node, "seq": 90000 + i, "ts": int(time.time() * 1000), "hmac": "deadbeef" * 8}
            frame.update({"motion": 1} if args.node == "A" else {"water": 1})
            c.publish(inject, json.dumps(frame))
            print(f"forged frame {i + 1} -> {inject}")
            time.sleep(0.5)
        print("done: no valid key, so ARES rejects on the signature and shadows", args.node)
    else:
        captured: list[dict] = []
        cap = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ares-sniffer")
        cap.on_message = lambda cl, u, m: captured.append(json.loads(m.payload))
        cap.connect(args.broker, args.port); cap.subscribe(f"ares/{args.node}/telemetry"); cap.loop_start()
        print(f"sniffing genuine frames on ares/{args.node}/telemetry (gateway must run with --mqtt-echo)...")
        for _ in range(20):
            time.sleep(0.5)
            if len(captured) >= 3:
                break
        cap.loop_stop()
        if not captured:
            raise SystemExit("captured nothing; start the gateway with --mqtt-echo")
        frame = captured[len(captured) // 2]
        print(f"captured a genuine signed frame (seq {frame['seq']}); replaying it...")
        for _ in range(args.frames):
            c.publish(inject, json.dumps(frame))
            time.sleep(0.5)
        print("done: signature is valid but the sequence is stale, so ARES rejects the replay")

    time.sleep(1)
    c.loop_stop()


if __name__ == "__main__":
    main()
