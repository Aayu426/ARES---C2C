"""One-command start for the ARES gateway.

  python run.py                       # simulator, no hardware needed
  python run.py --mode serial --ports COM3,COM4
  python run.py --sim-interval 0.5    # faster virtual world
"""
from __future__ import annotations

import argparse
import os
import sys

import uvicorn

from ares.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="ARES gateway")
    parser.add_argument("--mode", choices=["sim", "serial"], default="sim")
    parser.add_argument("--ports", default="", help="comma-separated COM ports for serial mode")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--keys", default="keys.json")
    parser.add_argument("--db", default="ares.db")
    parser.add_argument("--sim-interval", type=float, default=1.0)
    parser.add_argument("--mqtt-host", default="", help="broker IP to subscribe to for injected attack frames (e.g. the attacker PC)")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-echo", action="store_true", help="republish honest frames to ares/<node>/telemetry so an attacker can capture and replay them")
    args = parser.parse_args()
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    sys.stdout.reconfigure(line_buffering=True)   # logs reach files and pipes immediately

    ports = [p.strip() for p in args.ports.split(",") if p.strip()]
    app = create_app(mode=args.mode, ports=ports, keys_path=args.keys, db_path=args.db,
                     sim_interval=args.sim_interval, mqtt_host=args.mqtt_host,
                     mqtt_port=args.mqtt_port, mqtt_echo=args.mqtt_echo)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
