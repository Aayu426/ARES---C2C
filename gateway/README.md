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

## What happens after an attack (sim mode, default timings)

```
suppress_motion  ->  A is an outlier for 2+ cycles      (~2 s)
                 ->  SUSPICIOUS, integrity challenge     (~4 s)  "checking firmware, not identity"
                 ->  fingerprint mismatch -> SHADOW               "authentic but tampered"
                 ->  motion still CONFIRMED by C, WEBCAM -> alarm on, incident i-N written
spoof            ->  bad signature -> identity 0 -> SHADOW; challenges fail "impostor"
inject           ->  80 °C rejected by physics, no action, incident
restore          ->  RECOVERING 0/10 -> a challenge every 5 s -> TRUSTED at 10/10 (~50 s)
```

```
drift            ->  +0.1 °C per interval, every step legal -> drift_detected after ~30 s -> SUSPICIOUS
replay           ->  captured frames re-sent -> rejected on seq -> SHADOW (a reboot is allowed)
```

## Numbers and the explain button

```bash
.venv\Scripts\python measure.py --trials 20 --honest 120      # writes metrics.json, served at /metrics
set GEMINI_API_KEY=...                                        # optional; /explain falls back to a template
```

`known_fw.json` holds the known-good firmware fingerprints (defaults match the
simulator). Aayush replaces them with the SHA-256 of the honest builds.

## Layout

```
ares/canonical.py            canonical strings + HMAC (CONTRACTS section 2)
ares/transports/base.py      transport interface
ares/transports/serial_transport.py   one reader thread per COM port, NDJSON both ways
ares/transports/sim_transport.py      virtual A, B, C, WEBCAM + attacks
ares/store.py                SQLite tables
ares/bus.py                  event bus -> WebSocket clients
ares/trust.py                trust vector with debt + state machine
ares/physics.py              plausibility rules
ares/challenges.py           Adaptive Challenge Engine, known-good firmware table
ares/engine.py               ingest, verify, normalise to witnesses, consistency tick, consensus, alarm, incidents
ares/app.py                  FastAPI
run.py                       entrypoint
```
