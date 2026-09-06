# ARES Hardware Connections & Pin Mapping

This document outlines the complete physical wiring and pin configuration for the **ARES (Architecture for Resilient Edge Security)** target node prototype, utilizing a single ESP32 microcontroller integrated with environmental sensors, an optical verification camera, and status indicator LEDs.

---

## ESP32 Master Pin Map (Target Node)

| Component / Module | Component Pin | ESP32 Pin | Purpose & Status |
| :--- | :--- | :--- | :--- |
| **Water Sensor Module** | VCC / `+` | 3V3 | Power |
| | GND / `-` | GND | Ground |
| | AO (Analog Out) | GPIO 36 / VP | Analog Fluid-Level Telemetry Input |
| **PIR Motion Sensor** | Pin 1 (VCC / `+`) | 3V3 | Power |
| | Pin 2 (OUT / Signal) | GPIO 16 / RX2 | Digital Motion Detection Input |
| | Pin 3 (GND / `-` ) | GND | Ground |
| **OV7670 Camera Module** | 3.3V | 3V3 | Power |
| | GND | GND | Ground |
| | SDA | GPIO 13 / D13 | SCCB SDA |
| | SCL | GPIO 14 / D14 | SCCB SCL |
| | XLK | GPIO 17 / TX2 | Camera clock |
| | VS | GPIO 34 / D34 | Vertical sync |
| | HS | GPIO 33 / D33 | Horizontal sync |
| | PLK | GPIO 32 / D32 | Pixel clock |
| | D0 | GPIO 27 / D27 | Camera data |
| | D1 | GPIO 4 / D4 | Camera data |
| | D2 | GPIO 18 / D18 | Camera data |
| | D3 | GPIO 19 / D19 | Camera data |
| | D4 | GPIO 23 / D23 | Camera data |
| | D5 | GPIO 25 / D25 | Camera data |
| | D6 | GPIO 26 / D26 | Camera data |
| | D7 | GPIO 5 / D5 | Camera data |
| | RST | — | Floating / Not connected |
| | PWDN | — | Floating / Not connected |
| **Indicator LEDs (Shadow State)** | LED 1 (Anode) | GPIO 2 / D2 | Status Bit 1 |
| | LED 2 (Anode) | GPIO 12 / D12 | Status Bit 2 |

---

## Status Encoding Reference for Indicator LEDs

The hardware uses a two-bit indicator LED encoding scheme to visually display the node's real-time security state to judges and operators during the live demonstration:

* **00** (Both OFF) $\rightarrow$ Normal / Active Consensus
* **01** (D2 OFF, D12 ON) $\rightarrow$ Warning / Telemetry Drift Detected
* **10** (D2 ON, D12 OFF) $\rightarrow$ **Shadow State Active** (Isolated by ARES; attacker kept blind while mesh routes around it)
* **11** (Both ON) $\rightarrow$ Active Cryptographic Challenge in Progress
