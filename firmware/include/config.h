// Pin map and timing for ARES nodes. Matches hardware_connections.md where the
// two agree; change pins here, not in main.cpp.
#pragma once

#if defined(NODE_A)
#define NODE_ID "A"
#elif defined(NODE_B)
#define NODE_ID "B"
#else
#error "build with -DNODE_A or -DNODE_B"
#endif

// ---- sensors ----
#define PIR_PIN 16          // PIR OUT  (HAS_PIR)
#define WATER_PIN 36        // water AO, ADC1 input-only pin (HAS_WATER)
#define WATER_WET_THRESHOLD 1500   // raw ADC above this = wet; tune with the tray
#define TEMP_PIN 21         // DS18B20 data, 4.7k pull-up to 3V3 (HAS_TEMP_DS18B20)
#define I2C_SDA 21          // GY-906 MLX90614 SDA (HAS_TEMP_MLX)
#define I2C_SCL 22          // GY-906 MLX90614 SCL (HAS_TEMP_MLX); VIN -> 3V3, GND -> GND

// ---- outputs ----
#define ALARM_PIN 15        // buzzer (HAS_ALARM); active HIGH
#define LED1_PIN 2          // status bit 1 (HAS_STATUS_LEDS)  D2
#define LED2_PIN 12         // status bit 2 (HAS_STATUS_LEDS)  D12

// ---- timing ----
#define REPORT_MS 1000      // telemetry period
#define SERIAL_BAUD 115200
