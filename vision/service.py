"""ARES vision service: turns camera frames into signed witness messages.

Two witnesses, one process:
  C       the ESP32-CAM MJPEG stream (or any URL OpenCV can open)
  WEBCAM  the laptop camera

Each witness reports two claims every change and at least every 2 s:
  motion  YOLOv8n sees a person in the frame
  water   blue pixels cover enough of the floor ROI (add blue food colouring to the tray)

Messages follow CONTRACTS.md 3.2 and are signed with the witness's key. Challenges
arrive via GET /outbox/<node> and are answered on POST /inbox (gateway HTTP transport).

    python service.py --gateway http://127.0.0.1:8000 --webcam 0 --cam-url http://192.168.137.10:81/stream
    python service.py --calibrate WEBCAM        # click the four corners of the tray, then press s
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import threading
import time

import cv2
import numpy as np
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_PERSON_CONF = 0.5
WATER_BLUE_FRACTION = 0.08
REPORT_EVERY = 2.0
MOVE_PIXELS = 12        # centroid shift that counts as movement
MOTION_HOLD = 3.0       # seconds motion stays 1 after the last movement (like a PIR's hold time)

# HSV range for blue food colouring under indoor light; widen S/V if the venue is dim
BLUE_LO = np.array([95, 80, 50])
BLUE_HI = np.array([130, 255, 255])


# ------------------------------------------------------------------ signing

def sign(key: bytes, canonical: str) -> str:
    return hmac.new(key, canonical.encode(), hashlib.sha256).hexdigest()


def witness_canonical(node_id: str, seq: int, ts: int, claim: str, value: int) -> str:
    return f"{node_id}|{seq}|{ts}|{claim}|{value}"


def response_canonical(node_id: str, cid: str, nonce: str, fw: str) -> str:
    return f"{node_id}|{cid}|{nonce}|{fw}"


def load_keys() -> dict[str, bytes]:
    path = os.path.join(HERE, "keys.json")
    if not os.path.exists(path):
        raise SystemExit("vision/keys.json missing: copy C and WEBCAM from gateway/keys.json")
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: bytes.fromhex(v) for k, v in raw.items() if k in ("C", "WEBCAM")}


def load_fw() -> dict[str, str]:
    """This service's 'firmware fingerprint' per witness: a hash of this file plus the
    model name. Put the same values in gateway/known_fw.json."""
    with open(__file__, "rb") as fh:
        base = hashlib.sha256(fh.read()).hexdigest()
    return {"C": hashlib.sha256(f"C|{base}".encode()).hexdigest(),
            "WEBCAM": hashlib.sha256(f"WEBCAM|{base}".encode()).hexdigest()}


# ------------------------------------------------------------------ detectors

class Detectors:
    def __init__(self) -> None:
        from ultralytics import YOLO  # imported late so --calibrate works without torch loaded
        local = os.path.join(HERE, "yolov8n.pt")
        self.model = YOLO(local if os.path.exists(local) else "yolov8n.pt")   # downloads on first run

    def person(self, frame) -> tuple[int, float, tuple[float, float] | None]:
        """(present, confidence, centroid of the most confident person or None)"""
        res = self.model(frame, classes=[0], conf=MIN_PERSON_CONF, verbose=False, imgsz=416)[0]
        if len(res.boxes) == 0:
            return 0, 0.9, None
        i = int(res.boxes.conf.argmax())
        x1, y1, x2, y2 = res.boxes.xyxy[i].tolist()
        return 1, float(res.boxes.conf[i]), ((x1 + x2) / 2, (y1 + y2) / 2)

    @staticmethod
    def water(frame, roi: np.ndarray | None) -> tuple[int, float]:
        if roi is None:
            return 0, 0.0   # not calibrated: abstain (conf below the gateway's 0.6 floor)
        mask = np.zeros(frame.shape[:2], np.uint8)
        cv2.fillPoly(mask, [roi.astype(np.int32)], 255)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, BLUE_LO, BLUE_HI)
        inside = cv2.bitwise_and(blue, mask)
        frac = float(cv2.countNonZero(inside)) / max(1, cv2.countNonZero(mask))
        value = 1 if frac >= WATER_BLUE_FRACTION else 0
        conf = min(0.99, 0.6 + abs(frac - WATER_BLUE_FRACTION) * 4)
        return value, conf


# ------------------------------------------------------------------ one witness

class Witness:
    def __init__(self, node_id: str, source, key: bytes, fw: str, gateway: str, det: Detectors) -> None:
        self.node_id = node_id
        self.source = source
        self.key = key
        self.fw = fw
        self.gateway = gateway.rstrip("/")
        self.det = det
        self.seq = 0
        self.last_sent: dict[str, tuple[int, float]] = {}
        self.mode: str | None = None   # attack mode (stretch: the camera itself gets hacked)
        self.roi = self._load_roi()
        self.cap = None
        self.frame = None
        self.last_centroid: tuple[float, float] | None = None
        self.last_move_at = 0.0

    def _load_roi(self) -> np.ndarray | None:
        path = os.path.join(HERE, f"roi_{self.node_id}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return np.array(json.load(fh), dtype=np.float32)
        return None

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.source)
        ok = self.cap.isOpened()
        print(f"[{self.node_id}] source {self.source}: {'open' if ok else 'FAILED'}")
        return ok

    def post(self, path: str, body: dict) -> None:
        try:
            requests.post(f"{self.gateway}{path}", json=body, timeout=1.5)
        except requests.RequestException as exc:
            print(f"[{self.node_id}] post {path} failed: {exc}")

    def send(self, claim: str, value: int, conf: float, force: bool = False) -> None:
        now = time.time()
        prev = self.last_sent.get(claim)
        if not force and prev and prev[0] == value and now - prev[1] < REPORT_EVERY:
            return
        if self.mode == "suppress":
            value = 0
        self.seq += 1
        ts = int(now * 1000)
        msg = {"t": "wit", "node_id": self.node_id, "seq": self.seq, "ts": ts,
               "claim": claim, "value": value, "conf": round(conf, 2)}
        msg["hmac"] = sign(self.key, witness_canonical(self.node_id, self.seq, ts, claim, value))
        self.post("/witness", msg)
        self.last_sent[claim] = (value, now)

    def step(self) -> None:
        if self.cap is None:
            return
        ok, frame = self.cap.read()
        if not ok:
            time.sleep(0.2)
            return
        self.frame = frame
        present, pconf, centroid = self.det.person(frame)
        water, wconf = self.det.water(frame, self.roi)
        # motion = a person who moved recently; a person standing still is not motion,
        # which is exactly what the PIR on node A measures
        now = time.time()
        if present and centroid is not None:
            if self.last_centroid is not None:
                dx = centroid[0] - self.last_centroid[0]
                dy = centroid[1] - self.last_centroid[1]
                if (dx * dx + dy * dy) ** 0.5 >= MOVE_PIXELS:
                    self.last_move_at = now
            else:
                self.last_move_at = now      # a person appearing counts as movement
            self.last_centroid = centroid
        else:
            self.last_centroid = None
        motion = 1 if now - self.last_move_at < MOTION_HOLD else 0
        self.send("motion", motion, pconf if present else 0.9)
        if wconf >= 0.6:
            self.send("water", water, wconf)

    def poll_outbox(self) -> None:
        try:
            r = requests.get(f"{self.gateway}/outbox/{self.node_id}", timeout=1.5)
            msgs = r.json() if r.ok else []
        except requests.RequestException:
            return
        for msg in msgs:
            t = msg.get("t")
            if t == "chal":
                fw = self.fw if msg.get("type") == "integrity" else ""
                if self.mode and fw:
                    fw = "7a1c" + fw[4:]   # hacked camera reports a different fingerprint while attacking
                sig = sign(self.key, response_canonical(self.node_id, msg["challenge_id"], msg["nonce"], fw))
                self.post("/inbox", {"t": "resp", "node_id": self.node_id, "challenge_id": msg["challenge_id"],
                                     "fw": fw, "sig": sig})
            elif t == "atk":
                self.mode = None if msg.get("mode") == "restore" else msg.get("mode")
                print(f"[{self.node_id}] attack mode -> {self.mode}")


# ------------------------------------------------------------------ calibration

def calibrate(node_id: str, source) -> None:
    cap = cv2.VideoCapture(source)
    pts: list[list[int]] = []

    def on_mouse(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN and len(pts) < 4:
            pts.append([x, y])

    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", on_mouse)
    print("click the 4 corners of the tray, press s to save, q to quit")
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        for p in pts:
            cv2.circle(frame, tuple(p), 6, (0, 0, 255), -1)
        if len(pts) == 4:
            cv2.polylines(frame, [np.array(pts)], True, (0, 255, 0), 2)
        cv2.imshow("calibrate", frame)
        k = cv2.waitKey(30) & 0xFF
        if k == ord("s") and len(pts) == 4:
            with open(os.path.join(HERE, f"roi_{node_id}.json"), "w", encoding="utf-8") as fh:
                json.dump(pts, fh)
            print("saved")
            break
        if k == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


# ------------------------------------------------------------------ main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", default="http://127.0.0.1:8000")
    ap.add_argument("--webcam", type=int, default=0, help="OpenCV device index for WEBCAM; -1 to disable")
    ap.add_argument("--cam-url", default="", help="ESP32-CAM MJPEG URL for node C; empty to disable")
    ap.add_argument("--calibrate", default="", help="WEBCAM or C: pick the tray ROI and exit")
    ap.add_argument("--show", action="store_true", help="show the feeds with detections")
    args = ap.parse_args()

    if args.calibrate:
        src = args.webcam if args.calibrate == "WEBCAM" else args.cam_url
        calibrate(args.calibrate, src)
        return

    keys = load_keys()
    fws = load_fw()
    print("fingerprints for gateway/known_fw.json:", json.dumps({k: v for k, v in fws.items()}, indent=1))
    det = Detectors()
    witnesses: list[Witness] = []
    if args.webcam >= 0 and "WEBCAM" in keys:
        witnesses.append(Witness("WEBCAM", args.webcam, keys["WEBCAM"], fws["WEBCAM"], args.gateway, det))
    if args.cam_url and "C" in keys:
        witnesses.append(Witness("C", args.cam_url, keys["C"], fws["C"], args.gateway, det))
    witnesses = [w for w in witnesses if w.open()]
    if not witnesses:
        raise SystemExit("no camera opened")

    def outbox_loop():
        while True:
            for w in witnesses:
                w.poll_outbox()
            time.sleep(0.5)

    threading.Thread(target=outbox_loop, daemon=True).start()
    print("vision service running; ctrl-c to stop")
    while True:
        for w in witnesses:
            w.step()
            if args.show and w.frame is not None:
                cv2.imshow(w.node_id, w.frame)
        if args.show and (cv2.waitKey(1) & 0xFF) == ord("q"):
            break


if __name__ == "__main__":
    main()
