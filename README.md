# ARES — Adaptive Trust & Deception-Resistant Cyber-Physical Mesh

> **"A valid cryptographic key proves *who* a device is. It says nothing about whether what it reports is *true*. Authentic beats authenticated."**

**ARES (Architecture for Resilient Edge Security)** is a cyber-physical trust engine and deception-resistant sensor mesh designed to protect critical control infrastructure against compromised, hijacked, or spoofed edge sensors.

When an authenticated sensor is compromised—whether through physical tampering, memory injection, or firmware exploits—it can feed believable false telemetry into a control system without triggering traditional network alarms. ARES decouples identity from truth: it continuously scores every witness, interrogates suspicious claims with targeted active challenges, isolates doubted nodes into a **Shadow State** (where they continue reporting but cannot trigger physical actuators or alarms), and uses independent physical witnesses (neighbouring sensors, optical vision, and physics rules) to outvote liars.

---

## 🛠 System Architecture

```
                                  +---------------------------------------+
                                  |    Judge Attack Panel / Attacker PC   |
                                  |   (Local API / MQTT Network Ingress)  |
                                  +-------------------+-------------------+
                                                      |
                                                      v
+------------------+   Serial (USB)    +----------------------------------+    WebSocket    +----------------------------------+
|  ESP32 Node A    |------------------>|                                  |---------------->|   React Command Dashboard        |
|  (PIR + Buzzer)  |                   |                                  |                 |   - Real-time Telemetry & Mesh   |
+------------------+                   |         ARES GATEWAY             |                 |   - Trust Vector Over Time       |
+------------------+   Serial (USB)    |  - Multi-Transport Ingress       |                 |   - Consensus & Conflict Inspector|
|  ESP32 Node B    |------------------>|  - Trust Engine (Id, Int, Con)    |                 |   - Telemetry Drift Scrubber     |
|  (Water Sensor)  |                   |  - Active Challenge Scheduler    |                 |   - Gemini AI Incident Explainer |
+------------------+                   |  - Physical Shadow Isolator      |                 +----------------------------------+
+------------------+   MJPEG Stream    |  - SQLite Persistence            |
| ESP32-CAM (C) /  |------------------>|  - Gemini AI Explanation Engine  |
| Laptop WEBCAM    |  (Vision Service) |                                  |
+------------------+                   +----------------------------------+
```

ARES combines **multi-modal physical witnesses** with a central **Adaptive Trust Engine**:
1. **Sensor Edge Nodes (ESP32)**: Collect raw environmental telemetry, compute HMAC-SHA256 signatures over frames, respond to cryptographic & fingerprint challenges, and reflect node state on 2-bit physical status LEDs.
2. **Vision Witnesses (ESP32-CAM Node C & Laptop WEBCAM)**: Stream video feeds to an AI vision service running YOLOv8 person detection and HSV blue-pixel water tray detection to generate signed visual witness events.
3. **Network Ingress & MQTT Bridge**: Accepts external telemetry and attack payloads over MQTT (`ares/inject/#`), allowing remote machines on the network to attack the mesh.
4. **Gateway Core & Trust Engine**: Evaluates 3-axis trust vectors, enforces physical laws (e.g. rate-of-change limits, non-negative bounds), issues active challenges, and updates node states.
5. **Interactive Dashboard**: Modern Vite + React UI providing real-time mesh topology visualization, consensus conflict resolution views, drift scrubbers, incident inspection, and AI-generated root-cause explanations.

---

## 🛰 Hardware Map & Wiring Reference

### ESP32 Target Node Pin Configuration

| Component / Module | Component Pin | ESP32 Pin | Purpose & Description |
| :--- | :--- | :--- | :--- |
| **Water Sensor Module** | VCC / `+` | `3V3` | Power |
| | GND / `-` | `GND` | Ground |
| | AO (Analog Out) | `GPIO 36` (VP) | Analog Fluid-Level Telemetry Input |
| **PIR Motion Sensor** | Pin 1 (VCC / `+`) | `3V3` / `5V` | Power |
| | Pin 2 (OUT / Signal) | `GPIO 16` (RX2) | Digital Motion Detection Input |
| | Pin 3 (GND / `-`) | `GND` | Ground |
| **Physical Alarm** | Active Buzzer (`+`) | `GPIO 15` | Physical Alarm Output (Active HIGH) |
| **Status LEDs (Shadow State)** | LED 1 (Bit 1 Anode)| `GPIO 2` (D2) | Status Bit 1 |
| | LED 2 (Bit 2 Anode)| `GPIO 12` (D12) | Status Bit 2 |
| **DS18B20 Temp Sensor** *(Opt)*| DATA | `GPIO 21` | OneWire Temperature Data (4.7kΩ pull-up) |

### Physical 2-Bit Status LED Encoding
The ESP32 hardware displays real-time security state to operators via two indicator LEDs:
* `00` (Both OFF) $\rightarrow$ **Normal / Active Consensus** (Fully trusted, votes in consensus)
* `01` (D2 OFF, D12 ON) $\rightarrow$ **Warning / Telemetry Drift** (Outlier or gradual drift detected)
* `10` (D2 ON, D12 OFF) $\rightarrow$ **Shadow State Active** (Isolated by ARES; reports telemetry but isolated from triggering alarms/actuators)
* `11` (Both ON) $\rightarrow$ **Active Cryptographic Challenge** (Node currently undergoing identity or integrity interrogation)

---

## ⚡ Multi-Modal Witness Grid

| Witness ID | Type | Hardware | Monitored Claims | Transports Supported |
| :--- | :--- | :--- | :--- | :--- |
| **Node A** | Sensor Board | ESP32 DevKit + PIR Motion + Temp | `motion`, `temp` | USB Serial / MQTT |
| **Node B** | Sensor Board | ESP32 DevKit + Water Sensor | `water` | USB Serial / MQTT |
| **Node C** | Vision Node | ESP32-CAM (AI-Thinker) | `motion`, `water` | WiFi MJPEG Stream $\rightarrow$ Vision Service |
| **WEBCAM** | Vision Node | Laptop Integrated / USB Camera | `motion`, `water` | OpenCV Direct Feed $\rightarrow$ Vision Service |

*Both **Motion** and **Water** have 3 independent physical witnesses. When a compromised node lies, the remaining witnesses and physics rules outvote it in real time.*

---

## 🛡 Trust Model & Defense Mechanisms

ARES tracks a **3-Axis Trust Vector** $T = (T_{\text{id}}, T_{\text{int}}, T_{\text{con}})$ bounded between $0$ and $100$:

$$\text{Overall Trust} = \min(T_{\text{id}}, T_{\text{int}}, T_{\text{con}})$$

1. **Identity Trust ($T_{\text{id}}$)**:
   - Evaluates frame HMAC-SHA256 signatures against per-node secret keys.
   - Drops to `0` instantly on signature failure or frame sequence replay attacks.
2. **Integrity Trust ($T_{\text{int}}$)**:
   - Periodically issues nonce-based **Identity** and **Integrity** challenges.
   - Interrogates running firmware SHA-256 partition fingerprints. Compares reporting firmware hash against known clean signatures in `gateway/known_fw.json`.
3. **Consistency Trust ($T_{\text{con}}$)**:
   - Evaluates claims against majority consensus from independent peer witnesses.
   - Enforces physical laws (e.g. temperature cannot jump $> 5.0^\circ\text{C}$ in 1 second; water level cannot be negative).
   - Degrades rapidly when a node reports claims contradicting peer majority or physics bounds.

### Shadow State Isolation
When a node's trust drops below threshold ($\text{Overall} < 50$), ARES shifts the node into **Shadow State**:
- Telemetry continues to be logged for forensic analysis.
- The node is stripped of voting rights in consensus rounds.
- The node cannot trigger physical actuators or alarms.
- The physical indicator LEDs switch to `10`.

### Active Recovery Protocol
Trust in ARES is earned back slowly and never reset automatically:
- When restored, a node enters **Recovery State**.
- It must pass **10 consecutive active challenges** without a single failure before regaining full voting status.

---

## 💻 Repository Layout

```
ARES---C2C/
├── README.md                      # Primary project overview & documentation
├── CONTRACTS.md                   # Protocol message specifications, thresholds & API contracts
├── hardware_connections.md        # Physical ESP32 pinout & wiring reference
├── attacks/                       # Security testbed & attack scripts
│   ├── mqtt_attack.py             # Network-level MQTT spoof and replay attack tool
│   ├── replay.py                  # Local frame sniffing & sequence replay tool
│   └── spoof.py                   # Local signature forgery tool
├── docs/                          # Architecture guides & documentation
│   ├── PLAN.md                    # 48-Hour build plan and team owner lanes
│   ├── ESP32_CAM_SETUP.md         # ESP32-CAM flashing & Wi-Fi hotspot setup guide
│   ├── MQTT_SETUP.md              # MQTT broker configuration & attack setup
│   └── sample_stream.json         # Mock telemetry stream for frontend testing
├── firmware/                      # ESP32 C++ firmware (PlatformIO)
│   ├── platformio.ini             # Multi-environment build configs (nodeA, nodeB, malicious)
│   ├── make_secrets.py            # Generates include/secrets.h from gateway keys
│   ├── include/
│   │   ├── config.h               # Hardware pin definitions & thresholds
│   │   └── secrets.h.example      # Template for HMAC keys & firmware fingerprints
│   └── src/
│       └── main.cpp               # Telemetry loop, HMAC-SHA256, active challenges, status LEDs
├── frontend/                      # Command Center UI (Vite + React)
│   ├── package.json               # Node.js dependencies
│   ├── src/
│   │   ├── App.jsx / App.css      # Core application container & styles
│   │   ├── components/            # Interactive UI modules
│   │   │   ├── AlarmBanner.jsx    # Real-time physical alarm status banner
│   │   │   ├── AttackPanel.jsx    # Judge attack injection control panel
│   │   │   ├── ChallengeFeed.jsx  # Live active challenge interrogation log
│   │   │   ├── ConsensusConflictView.jsx # Majority voting & conflict inspector
│   │   │   ├── DriftScrubber.jsx  # Telemetry drift analysis tool
│   │   │   ├── EventTimeline.jsx  # Security incident timeline
│   │   │   ├── ExplainIncidentModal.jsx # Gemini AI incident analysis modal
│   │   │   ├── MeshTopologyGraph.jsx # Dynamic node connectivity & state graph
│   │   │   ├── MetricsPanel.jsx   # Performance metrics (detection latency, catch rate)
│   │   │   ├── NodeCard.jsx       # Real-time node status cards
│   │   │   ├── NodeDetailInspector.jsx # Deep-dive node telemetry & trust inspector
│   │   │   ├── TrustHistoryChart.jsx   # 3-axis trust vector timeline chart
│   │   │   └── TrustVectorPanel.jsx   # Real-time trust score breakdowns
│   │   └── views/                 # Navigation views (Overview, Mesh, Consensus, Attacks, etc.)
├── gateway/                       # ARES Gateway & Trust Engine (Python / FastAPI)
│   ├── run.py                     # One-command gateway launcher (sim, serial, mqtt)
│   ├── known_fw.json              # Whitelist of valid firmware partition SHA-256 hashes
│   ├── measure.py                 # Evaluation benchmark script (latency, catch rate)
│   └── ares/
│       ├── app.py                 # FastAPI WebSockets & HTTP endpoints
│       ├── challenges.py          # Adaptive Challenge Engine
│       ├── engine.py              # Central Trust Engine & Consensus Coordinator
│       ├── explain.py             # Gemini AI Incident Explainer & fallback engine
│       ├── physics.py              # Physical bounds & rate-of-change validation rules
│       ├── store.py                # SQLite database persistence layer
│       ├── trust.py                # 3-axis trust vector state machine
│       └── transports/            # Serial, MQTT, HTTP, and Sim ingress transports
└── vision/                        # AI Optical Witness Service (PyTorch + YOLOv8 + OpenCV)
    ├── service.py                 # Multi-camera detector service & ROI witness publisher
    ├── test_stream.py             # MJPEG camera stream connectivity test utility
    └── requirements.txt           # Python dependencies (ultralytics, opencv, torch)
```

---

## 🚀 Quickstart & Setup Guide

### 1. Environment & Keys Setup
Run the gateway once to generate cryptographic keys in `gateway/keys.json`:
```bash
cd gateway
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -c "from ares.engine import load_keys; load_keys('keys.json')"
```

Generate firmware secrets header:
```bash
cd ../firmware
python make_secrets.py
```

Copy keys for the vision service:
```bash
cd ../vision
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### 2. Flashing ESP32 Firmware
Connect Node A (PIR) and Node B (Water) over USB data cables:
```bash
cd firmware
# Build & flash Node A (e.g. COM3)
pio run -e nodeA -t upload --upload-port COM3

# Build & flash Node B (e.g. COM4)
pio run -e nodeB -t upload --upload-port COM4
```

---

### 3. Vision Witness Setup & Calibration
Calibrate the water tray ROI on your camera feed:
```bash
cd vision
# Calibrate webcam
.venv\Scripts\python service.py --calibrate WEBCAM

# Calibrate ESP32-CAM stream (optional)
.venv\Scripts\python service.py --calibrate C --cam-url http://192.168.137.23:81/stream
```

Start the vision service:
```bash
.venv\Scripts\python service.py --webcam 0 --show
```

---

### 4. Running the Gateway
Launch the ARES gateway in **serial mode** with hardware connected:
```bash
cd gateway
python run.py --mode serial --ports COM3,COM4
```

Or run in **pure simulation mode** (no hardware required):
```bash
python run.py --mode sim --sim-interval 1.0
```

To enable **MQTT Network Ingress** for remote network attacks:
```bash
python run.py --mode serial --ports COM3,COM4 --mqtt-host <BROKER_IP> --mqtt-echo
```

---

### 5. Launching the Command Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` to interact with the ARES Command Dashboard.

---

## 🧪 Judge Demo & Attack Scenarios

During live demonstration, attacks can be triggered via the **Judge Attack Panel** on the dashboard, command-line scripts, or over MQTT:

### 1. Motion / Water Suppression Attack (`suppress`)
- **Action**: Judge presses `SUPPRESS MOTION` on Node A.
- **Attack Effect**: Node A lies by suppressing motion telemetry while a person walks down the walkway.
- **ARES Defense**: Node C (Camera) and WEBCAM report `motion: 1`. Peer consensus outvotes Node A. Node A consistency score collapses, physical LEDs switch to `10` (**Shadow State**), and the physical buzzer alarm sounds on schedule.

### 2. Signature Forgery Attack (`spoof`)
- **Action**: Run `python attacks/spoof.py --node A` or `python attacks/mqtt_attack.py --mode spoof`.
- **Attack Effect**: An attacker injects forged telemetry frames without Node A's HMAC secret key.
- **ARES Defense**: Identity verification fails (`hmac_ok: false`). $T_{\text{id}}$ drops to `0`. The forged frame is flagged as a **REJECTED Ghost Reading**, and Node A is instantly isolated into Shadow State.

### 3. Frame Replay Attack (`replay`)
- **Action**: Run `python attacks/replay.py --node A` or `python attacks/mqtt_attack.py --mode replay`.
- **Attack Effect**: An attacker sniffs a valid, signed frame from the wire and replays it later.
- **ARES Defense**: Sequence number check detects stale or decreasing sequence (`seq <= last_seq`). Frame is rejected, triggering a `replay_rejected` incident and isolating the node.

### 4. Telemetry Drift Attack (`drift`)
- **Action**: Judge presses `DRIFT` on Node A.
- **Attack Effect**: Node A slowly corrupts temperature or fluid level telemetry over time.
- **ARES Defense**: Rate-of-change physics validation detects anomalous delta. Consistency degrades gradually, placing the node in `WARNING` (`01` LED) before pushing it into Shadow State.

---

## 🔮 Future Aspects & Technical Roadmap

As ARES evolves beyond the initial prototype stage, the following key architecture advancements will be integrated:

### 1. Dynamic P2P Mesh Routing & Autonomous Self-Healing
- Transition from gateway-assisted topology to a fully decentralized **Peer-to-Peer (P2P) ESP-NOW / Thread mesh**.
- Nodes shadowed by ARES will be automatically routed around at the physical radio layer, re-establishing alternative mesh relay paths dynamically.

### 2. On-Device TinyML & Edge Anomaly Detection
- Deploy lightweight neural networks (e.g. TensorFlow Lite for Microcontrollers / ESP-DL) directly onto **ESP32-S3 / ESP32-C6** microcontrollers.
- Detect physical sensor degradation, voltage anomalies, and acoustic/vibrational tampering at the silicon layer before frames leave the board.

### 3. Zero-Knowledge Telemetry Proofs (ZK-SNARKs)
- Implement succinct zero-knowledge proofs for sensor readings.
- Allows edge nodes to prove that raw telemetry falls within safe physical constraints and was sampled from authentic hardware without revealing sensitive raw environmental payloads over public networks.

### 4. Industrial Control System (ICS/SCADA) Protocol Connectors
- Develop native protocol adapters for **Modbus TCP/RTU**, **CAN bus (SAE J1939)**, **OPC UA**, and **DNP3**.
- Enables drop-in deployment of ARES trust engines into legacy power grids, water treatment plants, and automotive ECUs.

### 5. Automated Hardware-Rooted Re-Keying & PUF Integration
- Leverage **Physically Unclonable Functions (PUFs)** embedded in silicon to generate unique, un-copyable hardware fingerprints.
- Support automated dynamic session re-keying over the air (OTA) upon successful recovery from shadow state.

---

## 👥 Team & Credits

- **Yashraj**: Gateway Core, Trust Engine, Challenge Engine, Multi-Transport Ingress, Physics Rules & Integration.
- **Aayush**: ESP32 C++ Node Firmware, Hardware Circuit Design, Vision Service (YOLOv8 + OpenCV), MQTT Bridge.
- **Aryan**: Command Dashboard (Vite + React), Mesh Topology Graph, Trust Vector Visualizers, Judge Attack Panel.

---

## 📄 License
Designed & built for hackathon demonstration. Open source under the MIT License.
