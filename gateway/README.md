# ARES gateway

Everything the trust engine sees is a *witness*. Node A's `motion: 1` and camera C's
`{claim: "motion", value: 1}` become the same shape inside the engine, which is why
sensors, cameras and simulated twins are interchangeable.

## Run

```bash
cd gateway
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # Windows
.venv\Scripts\python run.py                        # simulator, no hardware
.venv\Scripts\python run.py --mode serial --ports COM3,COM4
```

First start generates `keys.json` (git-ignored). Copy the same keys into
`firmware/**/secrets.h` and `vision/keys.json`; every witness signs with its own key.

## Endpoints (CONTRACTS.md section 8)

| Method | Path              | Purpose                                                     |
|--------|-------------------|-------------------------------------------------------------|
| GET    | `/health`         | mode and known nodes                                        |
| GET    | `/state`          | full snapshot: nodes, claims, alarm, recent incidents       |
| WS     | `/ws`             | live events; first message is a `snapshot`                  |
| GET    | `/events/recent`  | last 200 events (for debugging)                             |
| POST   | `/witness`        | vision service posts `t: "wit"` messages (serial mode)      |
| POST   | `/attack`         | `{"type": "suppress_motion" \| "suppress_water" \| "spoof" \| "replay" \| "inject" \| "drift" \| "restore", "target": "A"}` |
| POST   | `/sim/env`        | sim only: `{"person": true, "water": false, "temp": 24.4}`  |

## Try it in sim mode

```bash
curl -X POST localhost:8000/sim/env -H "Content-Type: application/json" -d "{\"person\": true}"
curl -X POST localhost:8000/attack  -H "Content-Type: application/json" -d "{\"type\": \"suppress_motion\"}"
curl localhost:8000/state
```

After `suppress_motion`, node A reports `motion: 0` while C and WEBCAM report `1`.
After `spoof`, the target's frames fail signature verification and its identity drops
to 0 on the first bad frame.

## Layout

```
ares/canonical.py            canonical strings + HMAC (CONTRACTS section 2)
ares/transports/base.py      transport interface
ares/transports/serial_transport.py   one reader thread per COM port, NDJSON both ways
ares/transports/sim_transport.py      virtual A, B, C, WEBCAM + attacks
ares/store.py                SQLite tables
ares/bus.py                  event bus -> WebSocket clients
ares/engine.py               ingest, verify, normalise to witnesses (trust engine lands here in Phase 2)
ares/app.py                  FastAPI
run.py                       entrypoint
```
