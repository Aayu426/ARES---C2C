# ARES Contracts

Interface agreements between the three lanes. Nothing here is code. If a message, a
threshold or a rule is not in this file, it does not exist yet; change this file first,
then the code.

Team: Yashraj (gateway, trust engine, integration) · Aayush (firmware, hardware, vision
service) · Aryan (dashboard, judge attack panel).

Principle the whole system follows: **a valid key proves the device, never the reading.**
Device trust and claim trust are tracked separately.

---

## 1. Topology

| Id       | Hardware                          | Transport to gateway                 | Claims it witnesses            |
|----------|-----------------------------------|--------------------------------------|--------------------------------|
| `A`      | ESP32 #1: PIR + temp (optional)   | USB serial, 115200 baud, NDJSON      | `motion`, `temp` (physics only)|
| `B`      | ESP32 #2: water sensor            | USB serial, 115200 baud, NDJSON      | `water`                        |
| `C`      | ESP32-CAM                         | MJPEG stream over laptop hotspot; the vision service turns frames into witness messages | `motion`, `water` |
| `WEBCAM` | laptop camera, second angle       | local; vision service                | `motion`, `water`              |
| `ALARM`  | buzzer + LED on node A spare pins | serial command to `A`                | —                              |

Two claims matter for the demo: **motion** (is a person in the walkway) and **water** (is
there water in the tray). Each has three witnesses, so a two-against-one vote is possible.
Temperature has one witness and is checked only against physics.

The gateway runs on the laptop and has two transports behind one interface:
`serial` (real boards) and `sim` (simulator). Any witness can be real or simulated; the
trust engine cannot tell the difference and must not try to.

---

## 2. Identity and signing

Every witness (`A`, `B`, `C`, `WEBCAM`) has its own 32-byte secret key, generated once,
stored in an untracked header on the node (`secrets.h`) and in an untracked file on the
laptop (`gateway/keys.json`). Keys never appear in git.

Signatures are HMAC-SHA256, hex-encoded, over a **canonical string**, not over JSON
(JSON field order and float formatting differ between C++ and Python).

Canonical string for a telemetry frame:

```
node_id|seq|ts|motion|temp|water
```

- fields joined with `|`, in exactly this order
- absent fields written as empty (`A|41|120334|1||`)
- `temp` formatted with two decimals (`24.50`), never scientific notation
- `motion`, `water` are `0` or `1`

Canonical string for a challenge response:

```
node_id|challenge_id|nonce|fw
```

---

## 3. Messages

All messages are single-line JSON terminated by `\n` (NDJSON). Over serial the same
format is used in both directions.

### 3.1 Telemetry (node → gateway), every 1 s

```json
{"t":"tel","node_id":"A","seq":41,"ts":120334,"motion":1,"temp":24.50,"hmac":"9f2c…"}
{"t":"tel","node_id":"B","seq":41,"ts":120334,"water":0,"hmac":"c41a…"}
```

- `seq` monotonic per boot, starts at 1
- `ts` milliseconds since boot (ESP32 has no clock; the gateway stamps arrival time)
- a node sends only the fields it measures

### 3.2 Witness (vision service → gateway), on every change and at least every 2 s

```json
{"t":"wit","node_id":"C","seq":88,"ts":1725600000123,"claim":"motion","value":1,"conf":0.91,"hmac":"…"}
{"t":"wit","node_id":"WEBCAM","seq":90,"ts":1725600000140,"claim":"water","value":1,"conf":0.97,"hmac":"…"}
```

Canonical string: `node_id|seq|ts|claim|value` (conf is informational, not signed).
`value` is `0` or `1`. `conf` is the detector confidence 0–1.

The gateway normalises telemetry into the same shape internally: node `A`'s `motion:1`
becomes a witness `{node_id:"A", claim:"motion", value:1}`. **The trust engine only ever
sees witnesses.**

### 3.3 Challenge (gateway → node)

```json
{"t":"chal","challenge_id":"c-1043","type":"identity","nonce":"a3f9…16 bytes hex"}
{"t":"chal","challenge_id":"c-1044","type":"integrity","nonce":"…"}
```

### 3.4 Challenge response (node → gateway), within 2 s

```json
{"t":"resp","node_id":"A","challenge_id":"c-1043","fw":"","sig":"…"}
{"t":"resp","node_id":"A","challenge_id":"c-1044","fw":"e3b0c442…","sig":"…"}
```

- `identity`: `fw` is empty; `sig` = HMAC over `node_id|challenge_id|nonce|`
- `integrity`: `fw` is the SHA-256 of the running app partition (or the build constant
  `FW_FINGERPRINT` if the partition API is not used); `sig` covers it
- no response within 2 s counts as a **failed** challenge
- the gateway holds a table `known_good_fw = {A: "…", B: "…", C: "…", WEBCAM: "…"}`

### 3.5 Alarm command (gateway → node A)

```json
{"t":"alarm","on":1,"reason":"motion confirmed by C,WEBCAM"}
```

### 3.6 Attack command (gateway → malicious firmware), serial or simulator

```json
{"t":"atk","mode":"suppress"}    // report the claim as 0 regardless of the sensor
{"t":"atk","mode":"inject","temp":80.0}
{"t":"atk","mode":"restore"}     // honest reporting and honest fingerprint again
```

Honest firmware ignores `atk`. Malicious firmware reports a **different** `fw` while in
any attack mode, and the honest one after `restore`.

### 3.7 Status LEDs (gateway → node), on every state change

```json
{"t":"led","code":2}     // 0 normal · 1 warning (SUSPICIOUS/RECOVERING) · 2 shadow · 3 challenge in progress
```

### 3.8 HTTP nodes (vision service)

Camera witnesses are not on serial. They post witnesses to `POST /witness`, poll
`GET /outbox/<node>` (every 0.5 s) for `chal` and `atk` messages, and answer on
`POST /inbox` with the same `resp` shape as a board. A camera that stops polling for
10 s is unreachable and its challenges fail.

---

## 4. Trust vector

Per witness, three components 0–100, plus overall:

| Component     | Moves on                                                              |
|---------------|-----------------------------------------------------------------------|
| `identity`    | HMAC valid / invalid on every frame; identity challenge pass / fail   |
| `integrity`   | integrity challenge pass / fail                                       |
| `consistency` | agreement with other witnesses on the same claim; physics rules       |

```
overall = 0.35*identity + 0.35*integrity + 0.30*consistency
```

(Stretch: a fourth `behaviour` component from report-interval and variance baselines,
weights become 0.30 / 0.30 / 0.25 / 0.15.)

### 4.1 Update rules (trust debt)

Each component keeps a `debt` in 0–100. `component = 100 - debt`.

| Event                                   | Effect                                  |
|-----------------------------------------|-----------------------------------------|
| bad HMAC on a frame                     | identity debt = 100 immediately; counts as a failed challenge (SHADOW for 60 s) |
| replayed frame (seq not advancing; a reboot with seq near 1 and a reset clock is allowed) | same as bad HMAC |
| identity challenge failed / timed out   | identity debt = 100                     |
| integrity challenge failed              | integrity debt = 100                    |
| outlier on a claim vs other witnesses   | consistency debt += 30 per cycle (after one free cycle) |
| physics rule violated                   | consistency debt += 40                  |
| slow drift detected (short-term level ≥ 1.5 °C from the long-term baseline, ≥ 80 % of recent steps one-sided, every step within the rate rule) | consistency debt += 60, event `drift_detected`, incident |
| clean cycle (≥1 valid frame, no bad frame, not an outlier) | every debt -= 2 (repays slowly) |
| challenge passed                        | that component's debt -= 20; while RECOVERING every debt -= 10 as well |

Debt never goes below 0 or above 100. **Nothing resets instantly**; recovery is earned.

### 4.2 States

| State        | Rule                                                                   |
|--------------|------------------------------------------------------------------------|
| `TRUSTED`    | overall ≥ 70, every component ≥ 50, no failed challenge in the last 60 s |
| `SUSPICIOUS` | 40 ≤ overall < 70, **or any single component < 50** → a challenge is issued (see §6). The component floor matters: with consistency weighted 30 %, a node lying about every claim would otherwise never leave TRUSTED |
| `SHADOW`     | overall < 40, **or** any failed challenge. Frames still ingested and logged; witness excluded from every decision; challenged every 10 s |
| `UNKNOWN`    | claim-level, not node-level: witnesses conflict with no majority and no failed challenge → withhold action, raise `conflict`, keep challenging |
| `RECOVERING` | after `restore` / honest behaviour resumes from SHADOW: **10 consecutive passed challenges** (one every 5 s) before the vote counts again; progress exposed as `recovery: "6/10"` |

---

## 5. Consistency and physics rules (v1)

**Claim consistency** — every 1 s, per claim, among witnesses that are `TRUSTED` or
`RECOVERING`-but-not-yet-voting is excluded:

- majority value = value reported by more than half of the *voting* witnesses
- a witness that disagrees with the majority is an **outlier** this cycle; the first
  disagreeing cycle is free (real PIRs lag cameras by up to a second), debt starts on
  the second consecutive cycle
- a reading older than 3 s does not vote; vision witnesses count only if `conf ≥ 0.6`
- a claim with reporters but no majority (for example 1 vs 1) is `UNKNOWN`

**Physics rules** — violation adds consistency debt to the reporting witness:

| Rule                                            | Threshold                     |
|-------------------------------------------------|-------------------------------|
| temp rate of change                             | > 2.0 °C per second           |
| temp range                                      | < 5 °C or > 60 °C indoors     |
| temp zero-variance                              | identical to 0.01 °C for 120 s|
| PIR flapping                                    | > 5 transitions per second    |
| water flapping                                  | > 5 transitions per second    |

Physics can **block an action** on its own (an impossible reading never triggers the
alarm) even when no other witness exists. Physics never dismisses a corroborated claim.

---

## 6. Challenge selection (the Adaptive Challenge Engine)

The type of doubt picks the challenge. Every choice emits a human-readable `reason`.

| Doubt                                          | Challenge issued        | Reason string example                                  |
|------------------------------------------------|-------------------------|--------------------------------------------------------|
| HMAC failures / identity debt rising           | `identity` (nonce)      | "signature errors on A → proving identity"             |
| outlier on a claim, identity fine              | `integrity` (fingerprint) | "A disagrees with C, WEBCAM on motion → checking firmware, not identity" |
| integrity fine, still outlier                  | re-poll other witnesses, mark claim `UNKNOWN` if no majority | "A authentic and unmodified but isolated → escalating" |
| node in SHADOW                                 | alternate identity / integrity every 10 s | "shadowed node A re-tested"                  |
| node RECOVERING                                | alternate, every 5 s, counting passes | "recovery 6/10"                                |

Outcomes:

- identity passes + integrity fails → **"authentic but tampered"** → SHADOW
- identity fails → **"impostor"** → SHADOW (identity 0)
- both pass but still outlier → claim `UNKNOWN`, node stays SUSPICIOUS, human escalation

---

## 7. Decision policy (consensus)

For each claim, each cycle:

1. collect values from voting witnesses (TRUSTED only; SHADOW excluded; RECOVERING
   excluded until 10/10)
2. if a majority agrees on `1` → claim **confirmed** → `incident` + `alarm on`
3. if a majority agrees on `0` → claim clear → `alarm off`
4. if no majority (e.g. 1 vs 1) → `UNKNOWN`, no action, `conflict` event, challenge
   the disagreeing nodes
5. a physics-violating reading is dropped before step 1

The alarm therefore rings **only on corroborated evidence**, and a single shadowed liar
cannot suppress a claim two other witnesses can see.

---

## 8. Gateway HTTP + WebSocket

### 8.1 HTTP

| Method | Path                       | Body / response                                                 |
|--------|----------------------------|-----------------------------------------------------------------|
| POST   | `/witness`                 | a §3.2 message (vision service → gateway)                       |
| GET    | `/outbox/{node}`           | pending `chal` / `atk` messages for an HTTP node (drained on read) |
| GET    | `/capture/{node}?n=5`      | last valid raw frames of a node, signatures included (what a wire-tap sees; used by `attacks/replay.py`) |
| POST   | `/inbox`                   | `resp` (or `wit`) from an HTTP node                             |
| POST   | `/attack`                  | `{"type":"suppress_motion"\|"suppress_water"\|"spoof"\|"replay"\|"inject"\|"restore","target":"A"\|"B"}` |
| GET    | `/state`                   | full snapshot: nodes, claims, incidents (dashboard initial load)|
| GET    | `/explain/{incident_id}`   | `{"text":"…3 sentences…","source":"gemini"\|"template"}`. Uses Gemini when `GEMINI_API_KEY` is set (model from `GEMINI_MODEL`, default `gemini-2.5-flash`), otherwise a deterministic template with the same shape. Read-only: it cannot change trust, state or actions |
| GET    | `/metrics`                 | output of `gateway/measure.py` (`metrics.json`): median/p95 detection latency, catch rate, false positives per hour of honest running |

`/attack` in `sim` mode performs the attack inside the simulator; in `serial` mode it
sends the §3.6 command to the target board. Real boards cannot impersonate themselves,
so in `serial` mode `spoof` and `replay` are performed by the gateway acting as the
attacker (forged frames; captured frames re-sent). `attacks/spoof.py` and
`attacks/replay.py` do the same from a separate laptop through `/inbox`, for a judge
who wants to see the attack come from outside. Every attack is idempotent; `restore` always returns to baseline.

### 8.2 WebSocket `/ws` events (gateway → dashboard)

```json
{"e":"node_update","node_id":"A","state":"TRUSTED","identity":100,"integrity":100,"consistency":92,"overall":97,"recovery":null,"last":{"motion":1,"temp":24.5}}
{"e":"witness","node_id":"C","claim":"motion","value":1,"conf":0.91}
{"e":"challenge_issued","node_id":"A","challenge_id":"c-1044","type":"integrity","reason":"A disagrees with C, WEBCAM on motion → checking firmware, not identity"}
{"e":"challenge_result","node_id":"A","challenge_id":"c-1044","type":"integrity","passed":false,"detail":"fingerprint mismatch"}
{"e":"state_change","node_id":"A","from":"SUSPICIOUS","to":"SHADOW","reason":"integrity challenge failed"}
{"e":"claim","claim":"motion","status":"CONFIRMED","by":["C","WEBCAM"],"against":["A"]}
{"e":"conflict","claim":"motion","witnesses":{"A":0,"WEBCAM":1},"status":"UNKNOWN"}
{"e":"incident","id":"i-17","claim":"motion","summary":"motion confirmed by C, WEBCAM while A reported none; A failed integrity","ts":1725600000123}
{"e":"alarm","on":true,"reason":"motion confirmed by C, WEBCAM"}
{"e":"escalation","node_id":"A","claim":null,"reason":"A is authentic and unmodified but isolated on its claim -> human decision"}
{"e":"drift_detected","node_id":"A","claim":"temp","detail":"slow drift: +3.6 °C from baseline in steps of at most 0.36 °C, each too small for any alarm"}
{"e":"replay_rejected","node_id":"B","seq":182,"detail":"replayed frame rejected: seq 182 already seen (last 186)"}
```

Aryan builds against `docs/sample_stream.json` (a hand-written 60 s sequence of these
events) until the gateway exists.

---

## 9. Judge attack panel (phone page)

Six buttons, one target selector where relevant, nothing else:

`SUPPRESS MOTION (A)` · `SUPPRESS WATER (B)` · `SPOOF (A)` · `REPLAY (A)` · `INJECT TEMP (A)` · `RESTORE`

Each button calls `POST /attack` and shows the gateway's one-line acknowledgement.

---

## 10. Demo script, 5 minutes

```
0:00  Baseline. A, B, C, WEBCAM all TRUSTED. "This node is authenticated. Watch it lie."
0:30  SUPPRESS MOTION. Aayush walks the taped walkway.
      C: person. WEBCAM: person. A: nothing → outlier → integrity challenge
      → nonce OK (really A) → fingerprint FAILS → A SHADOW
      → motion CONFIRMED by 2 of 3 → buzzer. "The alarm rings anyway."
1:45  SUPPRESS WATER. Blue water into the tray. Same machinery, different lie.
2:45  SPOOF, then REPLAY. Each dies in seconds to HMAC / sequence window.
3:15  INJECT TEMP. 80 °C rejected by physics alone. "No neighbours needed."
3:35  Numbers card: median and p95 detection latency, false positives per hour.
3:50  RESTORE. A → RECOVERING, "6/10 passed" climbing. "Trust is earned, not reset."
4:15  Explain incident (Gemini). "The AI explained. It never decided."
4:30  Close: authentic ≠ honest. Failure modes we own. Future work. Questions.
```

---

## 11. Failure modes we state out loud

- a **majority of witnesses colluding** inverts consensus; ARES cannot detect a lie the
  majority agrees on (mitigation: independent modalities — a PIR and two cameras rarely
  share an exploit)
- a **compromised gateway** compromises everything; distributed authorisation is future
  work
- **damage vs deception** can look identical at low trust; ARES reports UNKNOWN rather
  than guessing
- the AI layer is advisory; if Gemini is wrong, nothing changes, because it cannot act

---

## 12. Repository layout

```
ARES/
  CONTRACTS.md          this file
  README.md
  docs/PLAN.md          48-hour plan (mirror of the shared page)
  docs/sample_stream.json
  firmware/             Aayush — honest/, malicious/, shared/ (PlatformIO)
  vision/               Aayush — YOLO + blue-water detector, posts /witness
  gateway/              Yashraj — FastAPI, serial + sim transports, trust engine
  dashboard/            Aryan — Vite + React
```
