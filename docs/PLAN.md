# ARES — 48-hour build plan

Mirror of the shared plan page (tick boxes live there). Three parallel lanes; Phase 0 is
done together, after that nobody waits on anybody. Every window leaves something
demoable.

Lanes: **Yashraj** gateway, trust engine, simulator, Gemini, integration ·
**Aayush** firmware, hardware, vision service, props · **Aryan** dashboard, attack panel,
slides.

## Prep (before the clock, one day)

Rules first: wiring, environment setup and design documents only. No application code.

- Yashraj: repo layout, `CONTRACTS.md`, `docs/sample_stream.json`; Python 3.11 venv
  (fastapi, uvicorn, pyserial, sqlalchemy, websockets); Node 20; ultralytics + opencv
  installed and YOLOv8n weights downloaded; confirm YOLO detects a person on the webcam.
- Aayush: both ESP32s flash and print to serial (note COM ports); PIR on #1, water on
  #2, temp on #1 only if it reads clean in 10 minutes; ESP32-CAM streams to a browser
  over the laptop hotspot — 2-hour cap, then webcam-only; buzzer + LED on spare pins; 5 V
  supply for the CAM; USB cables that carry data; props (tray, blue-dyed water, taped
  walkway both cameras see).
- Aryan: Vite + React + Recharts scaffold runs; dashboard sketched on paper (node cards,
  witness row, trust panel, event feed, alarm banner); the judge's phone on the hotspot.

Done when: both boards print readings, CAM streams or the webcam decision is made, YOLO
sees a person, everyone can recite the demo script.

## Phase 1 · hours 0–8 · skeleton

- Yashraj: gateway with `serial` and `sim` transports behind one interface; simulator for
  A, B, C, WEBCAM with suppress/inject/drift flags; SQLite tables; WebSocket `node_update`
  and `witness`; one-command start.
- Aayush: honest firmware sending contract NDJSON every 1 s; vision service (CAM stream +
  webcam → YOLO person, blue-pixel water in ROI → `POST /witness`); ROI calibration.
- Aryan: node cards + witness row from `sample_stream.json`, then the real socket; event
  feed; reconnecting client.

Done when: walking the walkway lights three motion chips; the simulator does the same.

## Phase 2 · hours 8–20 · trust engine and identity

- Yashraj: trust vector (identity, integrity, consistency), states, claim consistency,
  physics rules, trust debt, HMAC verification.
- Aayush: per-node keys (untracked), HMAC-SHA256 on frames, identity challenge over
  serial, firmware fingerprint, vision service signs its witnesses.
- Aryan: trust panel, trust-over-time chart, reasons in the event feed.

Done when: simulator flag "PIR lies" collapses A's consistency in under 5 s; all other
witnesses stay green for 30 minutes.

## Phase 3 · hours 16–30 · challenge, shadow, consensus, alarm (the demo)

- Yashraj: Adaptive Challenge Engine with reason strings; fingerprint verification;
  shadow state; consensus with physics block and UNKNOWN; alarm command; `/attack` API.
- Aayush: malicious firmware (suppress / inject / restore, different fingerprint); alarm
  handler; flash A and B; tune vision on venue-like light.
- Aryan: challenge reasoning feed; shadow visuals; alarm banner; judge attack panel.

Done when: SUPPRESS MOTION on the phone + a walk-through sounds the buzzer while A sits
in shadow; same for water with the tray.

## Phase 4 · hours 30–40 · remaining attacks, recovery, AI, numbers

- Yashraj: spoof + replay detection; INJECT rejected by physics; recovery gating 10/10;
  `/explain` with Gemini and template fallback; 20-run numbers script.
- Aayush: spoof and replay scripts; RESTORE without reflash.
- Aryan: recovery ring; explain button ("advisory only"); metrics card; projector pass.

Done when: every panel button reacts within 5 s; RESTORE brings A back over a minute.

## Phase 5 · hours 40–48 · rehearse and pitch

Two rehearsals (second with the CAM unplugged mid-demo), five slides, Q&A split, README,
sleep once.

Demo script: see `CONTRACTS.md` §10.

## Stretch only if ahead at hour 36

Slow drift in simulation with time-compressed replay · hacking the camera node ·
behaviour score · automatic hot-swap of a silent node.

## Cut for 48 hours (admitted on slide 5)

Full measurement harness · separate veto logic · trust graph · digital twin · second
water node · MQTT/WiFi for sensor nodes.

## Risks → pre-agreed answers

| Risk                              | Answer                                                        |
|-----------------------------------|---------------------------------------------------------------|
| CAM will not stream               | 2-hour cap in prep; webcam-only; challenge breaks a 1-vs-1 tie |
| YOLO misses under stage light     | walk slowly facing cameras; taped walkway inside both ROIs     |
| temp sensor flaky                 | unplug, drop INJECT, never mention                             |
| a board dies on stage             | simulator mode for that node, say so, continue                 |
| Yashraj overloaded                | Aryan takes numbers script + attack wiring; Aayush takes alarm |
| no internet / Gemini quota        | template explanation, identical button                         |
| judge presses out of order        | every attack idempotent; RESTORE returns to baseline           |
| 3 a.m. scope creep                | nothing outside this file gets built                           |
