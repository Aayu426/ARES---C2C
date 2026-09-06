# Turning on the ESP32-CAM (Node C)

Node C is **not** like nodes A and B. It has no USB port and does not run our node
firmware. It runs a camera streaming firmware, joins the laptop hotspot, and serves
MJPEG video. The vision service on the laptop reads that video, runs YOLO on it, and
posts Node C's `motion` / `water` witnesses. So Node C is a real ARES witness, but the
detection happens on the laptop, not on the camera.

```
ESP32-CAM  --(MJPEG over hotspot WiFi)-->  vision service (YOLO)  --(signed witness)-->  gateway
```

## 0. What you need

- The **ESP32-CAM** module (AI-Thinker, black board with the OV2640 camera on a ribbon).
- A way to flash it, because it has no USB. One of:
  - an **ESP32-CAM-MB** baseboard (clips under the CAM, has a micro-USB and CH340), or
  - a **USB-to-TTL / FTDI adapter** (CP2102 or CH340) with jumper wires.
- A solid **5 V supply**. Brown-outs look like random reboots and "camera init failed".
- The laptop **hotspot** on (2.4 GHz — ESP32 has no 5 GHz).

## 1. Wiring to flash (only needed while flashing)

With an FTDI adapter set to **5 V**:

| FTDI    | ESP32-CAM |
|---------|-----------|
| 5V      | 5V        |
| GND     | GND       |
| TX      | U0R (RX)  |
| RX      | U0T (TX)  |
| —       | **IO0 → GND** (jumper on, to enter flash mode) |

With an ESP32-CAM-MB baseboard: just plug the CAM in and connect micro-USB; press the
tiny RST after starting the upload. No IO0 jumper needed on most MB boards.

## 2. Flash the streaming firmware (Arduino IDE — most reliable)

1. Arduino IDE → Boards Manager → install **esp32 by Espressif**.
2. **Tools → Board → AI Thinker ESP32-CAM**.
3. **File → Examples → ESP32 → Camera → CameraWebServer**.
4. At the top of the sketch:
   - keep `#define CAMERA_MODEL_AI_THINKER` (comment out the others),
   - set your hotspot:
     ```cpp
     const char* ssid     = "<YOUR_HOTSPOT_SSID>";
     const char* password = "<YOUR_HOTSPOT_PASSWORD>";
     ```
5. IO0 jumper to GND (or MB board ready), press RST, click **Upload**.
6. When it says "Connecting…", tap RST once. After "Hard resetting", **remove the IO0
   jumper** and press RST again to run.

## 3. Get the stream URL

Open **Tools → Serial Monitor at 115200**. After it joins the hotspot it prints:

```
WiFi connected
Camera Ready! Use 'http://192.168.137.23' to connect
```

- Open `http://192.168.137.23` in a browser once → click **Start Stream** → you should
  see live video. That confirms the camera works.
- The raw stream the vision service needs is `http://192.168.137.23:81/stream`.

Quick test without a browser (from the laptop):
```bash
cd vision
.venv\Scripts\python test_stream.py http://192.168.137.23:81/stream
```

## 4. Add Node C to the running system

Restart the vision service with the camera URL (keep the webcam too):

```bash
cd vision
.venv\Scripts\python service.py --gateway http://127.0.0.1:8000 --webcam 0 --cam-url http://192.168.137.23:81/stream --show
```

Now the gateway's `/state` shows **C online=True**, and the dashboard's Node C card
tracks what the ESP32-CAM sees. Calibrate its tray region once:

```bash
.venv\Scripts\python service.py --calibrate C --cam-url http://192.168.137.23:81/stream
```

## 5. If it fights you — the 2-hour cap

The ESP32-CAM is the flakiest part of the build. If after ~2 hours it will not stream
(camera init fails, constant reboots, won't join the hotspot), **stop and go
webcam-only**. The demo works with just the laptop webcam as the camera witness; Node C
is the optional second angle. Do not let it eat the day.

Common failures:
- "camera init failed 0x20004" → bad 5 V supply, or a loose ribbon. Reseat the ribbon,
  use a better supply.
- won't upload → IO0 not on GND, or TX/RX swapped, or baud too high (try 115200).
- joins WiFi then reboots when streaming → supply can't hold the current; use 5 V 2 A.
- can't reach the IP → PC and CAM must be on the same hotspot; allow it through the
  firewall.
