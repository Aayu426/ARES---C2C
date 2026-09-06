# ARES vision service

Turns the ESP32-CAM stream (node `C`) and the laptop webcam (`WEBCAM`) into signed
witness messages for the gateway. Both report two claims:

- **motion** — YOLOv8n sees a person (class 0) with confidence ≥ 0.5
- **water** — blue pixels cover ≥ 8 % of the tray ROI (put a drop of blue food colouring
  in the demo water; it makes detection lighting-proof)

## Setup

```bash
cd vision
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt     # CPU torch + ultralytics + opencv, ~5 min
```

Copy the `C` and `WEBCAM` entries from `../gateway/keys.json` into `vision/keys.json`
(git-ignored):

```json
{"C": "<hex>", "WEBCAM": "<hex>"}
```

## Calibrate the tray once per camera

```bash
.venv\Scripts\python service.py --calibrate WEBCAM
.venv\Scripts\python service.py --calibrate C --cam-url http://192.168.137.10:81/stream
```

Click the four corners of the tray, press `s`. Saved as `roi_<node>.json`.

## Run

```bash
.venv\Scripts\python service.py --webcam 0 --cam-url http://192.168.137.10:81/stream --show
```

Leave `--cam-url` out to run webcam-only. On start it prints the fingerprints to put
in `../gateway/known_fw.json` under `C` and `WEBCAM` (the gateway's integrity
challenge checks them).

The service polls `GET /outbox/<node>` for challenges and attack commands and posts
responses to `POST /inbox`, so both cameras are full nodes: they can be challenged,
shadowed, and (stretch) hacked like the sensor boards.

## ESP32-CAM

Flash the stock `CameraWebServer` example (AI-Thinker board), point it at the laptop
hotspot, open `http://<cam-ip>` once to confirm, then use `http://<cam-ip>:81/stream`
as `--cam-url`. Give it a solid 5 V supply; brown-outs look like random reboots.
Two-hour cap: if it will not stream, go webcam-only and stop.

## Tuning

- Dim venue: lower `BLUE_LO[1]` (saturation) and `BLUE_LO[2]` (value) in `service.py`.
- Person missed: walk slowly, face the camera, or lower `MIN_PERSON_CONF` to 0.4.
- CPU too slow: `imgsz=320` in `Detectors.person`.
