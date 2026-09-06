# ARES — Adaptive Trust & Deception-Resistant Cyber-Physical Mesh

A valid key proves *who* a device is. It says nothing about whether what it reports is
*true*. ARES treats those as two different questions.

Authenticated edge sensors are assumed honest, so one hijacked sensor can feed
believable false readings into a control system without tripping a single network
alarm. ARES scores every witness continuously, interrogates suspicious claims with a
challenge matched to the type of doubt, places doubted nodes in a shadow state where
they keep reporting but cannot trigger anything, and lets independent witnesses
(neighbouring sensors, cameras, plain physics) outvote a liar. Trust is earned back
slowly, never reset.

## Demo hardware

| Witness | Hardware                                | Claims       |
|---------|-----------------------------------------|--------------|
| A       | ESP32 · PIR motion · temp (physics only)| motion, temp |
| B       | ESP32 · water sensor                    | water        |
| C       | ESP32-CAM, vision service on the laptop | motion, water|
| WEBCAM  | laptop camera, second angle             | motion, water|

Motion and water each have three witnesses. A judge presses an attack on a phone; the
hijacked node lies; the other two witnesses and the challenge engine catch it live.

## Documents

- [`CONTRACTS.md`](CONTRACTS.md) — every message, threshold and rule. Change this first.
- [`docs/PLAN.md`](docs/PLAN.md) — the 48-hour build plan with owner lanes.
- `docs/sample_stream.json` — 60 seconds of example dashboard events (hand-written data
  matching CONTRACTS §8.2) so the dashboard can be built before the gateway exists.

## Team

Yashraj — gateway, trust engine, simulator, integration ·
Aayush — firmware, hardware, vision service ·
Aryan — dashboard, judge attack panel

## Status

Design and contracts only. All code is written during the hackathon.
