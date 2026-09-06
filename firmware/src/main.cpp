// ARES node firmware — honest and malicious builds from one source.
//
// Every REPORT_MS the node prints one signed NDJSON telemetry line on USB serial
// (CONTRACTS.md 3.1). It answers challenges (3.3/3.4), drives the alarm (3.5), and the
// malicious build obeys attack commands (3.6). The honest build ignores them.
//
// Signatures: HMAC-SHA256 over the canonical pipe string, never over JSON.
//   telemetry:  node_id|seq|ts|motion|temp|water
//   response:   node_id|challenge_id|nonce|fw

#include <Arduino.h>
#include <ArduinoJson.h>
#include "mbedtls/md.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "config.h"
#include "secrets.h"

#ifdef HAS_TEMP_DS18B20
#include <OneWire.h>
#include <DallasTemperature.h>
static OneWire oneWire(TEMP_PIN);
static DallasTemperature temps(&oneWire);
#endif
#ifdef HAS_TEMP_MLX
#include <Wire.h>
#include <Adafruit_MLX90614.h>
static Adafruit_MLX90614 mlx;
static bool mlxOk = false;
#endif

// ---------------------------------------------------------------- identity
static uint8_t g_key[32];
static char g_fw[65];              // SHA-256 of the running app partition, hex

static int hexval(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return 0;
}

static void loadKey() {
  const char* hex = NODE_KEY_HEX;
  for (int i = 0; i < 32; i++) g_key[i] = (hexval(hex[2 * i]) << 4) | hexval(hex[2 * i + 1]);
}

static void hmacHex(const char* msg, char out[65]) {
  uint8_t digest[32];
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_hmac(info, g_key, 32, (const uint8_t*)msg, strlen(msg), digest);
  static const char* h = "0123456789abcdef";
  for (int i = 0; i < 32; i++) { out[2 * i] = h[digest[i] >> 4]; out[2 * i + 1] = h[digest[i] & 15]; }
  out[64] = 0;
}

static void computeFirmwareFingerprint() {
  uint8_t sha[32];
  const esp_partition_t* running = esp_ota_get_running_partition();
  if (running && esp_partition_get_sha256(running, sha) == ESP_OK) {
    static const char* h = "0123456789abcdef";
    for (int i = 0; i < 32; i++) { g_fw[2 * i] = h[sha[i] >> 4]; g_fw[2 * i + 1] = h[sha[i] & 15]; }
    g_fw[64] = 0;
  } else {
    strcpy(g_fw, "0000000000000000000000000000000000000000000000000000000000000000");
  }
}

// ---------------------------------------------------------------- attack state
enum Mode { HONEST, SUPPRESS, INJECT, DRIFT };
static Mode g_mode = HONEST;
static float g_injectTemp = 80.0f;
static float g_drift = 0.0f;

// The fingerprint the node *reports*. Honest build: the real one. Malicious build:
// the honest build's fingerprint while idle (it hides), its real one while attacking.
static const char* reportedFingerprint() {
#ifdef MALICIOUS
  return g_mode == HONEST ? HONEST_FW_FINGERPRINT : g_fw;
#else
  return g_fw;
#endif
}

// ---------------------------------------------------------------- outputs
static void setAlarm(bool on) {
#ifdef HAS_ALARM
  digitalWrite(ALARM_PIN, on ? HIGH : LOW);
#endif
}

static void setStatusLeds(int code) {   // 0 normal, 1 warning, 2 shadow, 3 challenge
#ifdef HAS_STATUS_LEDS
  digitalWrite(LED1_PIN, (code & 2) ? HIGH : LOW);
  digitalWrite(LED2_PIN, (code & 1) ? HIGH : LOW);
#endif
}

// ---------------------------------------------------------------- sensors
static int readMotion() {
#ifdef HAS_PIR
  return digitalRead(PIR_PIN) == HIGH ? 1 : 0;
#else
  return -1;
#endif
}

static int readWaterRaw() {
#ifdef HAS_WATER
  return analogRead(WATER_PIN);
#else
  return -1;
#endif
}

static bool readTemp(float& out) {
#if defined(HAS_TEMP_DS18B20)
  temps.requestTemperatures();
  float t = temps.getTempCByIndex(0);
  if (t == DEVICE_DISCONNECTED_C || t < -40 || t > 125) return false;
  out = t;
  return true;
#elif defined(HAS_TEMP_MLX)
  if (!mlxOk) return false;
  float t = mlx.readObjectTempC();     // what the sensor is pointed at; a hand in front shows immediately
  if (isnan(t) || t < -40 || t > 125) return false;
  out = t;
  return true;
#else
  return false;
#endif
}

// ---------------------------------------------------------------- telemetry
static uint32_t g_seq = 0;

static void sendTelemetry() {
  g_seq++;
  uint32_t ts = millis();
  int motion = readMotion();
  int waterRaw = readWaterRaw();
  int water = waterRaw < 0 ? -1 : (waterRaw > WATER_WET_THRESHOLD ? 1 : 0);
  float temp; bool hasTemp = readTemp(temp);

#ifdef MALICIOUS
  if (g_mode == SUPPRESS) { if (motion >= 0) motion = 0; if (water >= 0) water = 0; }
  if (g_mode == INJECT && hasTemp) temp = g_injectTemp;
  if (g_mode == DRIFT && hasTemp) { g_drift += 0.1f; temp += g_drift; }
#endif

  char motionS[4] = "", tempS[16] = "", waterS[4] = "";
  if (motion >= 0) snprintf(motionS, sizeof motionS, "%d", motion);
  if (hasTemp) snprintf(tempS, sizeof tempS, "%.2f", temp);
  if (water >= 0) snprintf(waterS, sizeof waterS, "%d", water);

  char canonical[96];
  snprintf(canonical, sizeof canonical, "%s|%lu|%lu|%s|%s|%s", NODE_ID, (unsigned long)g_seq, (unsigned long)ts, motionS, tempS, waterS);
  char sig[65]; hmacHex(canonical, sig);

  Serial.printf("{\"t\":\"tel\",\"node_id\":\"%s\",\"seq\":%lu,\"ts\":%lu", NODE_ID, (unsigned long)g_seq, (unsigned long)ts);
  if (motion >= 0) Serial.printf(",\"motion\":%d", motion);
  if (hasTemp) Serial.printf(",\"temp\":%s", tempS);
  if (water >= 0) Serial.printf(",\"water\":%d,\"water_raw\":%d", water, waterRaw);
  Serial.printf(",\"hmac\":\"%s\"}\n", sig);
}

// ---------------------------------------------------------------- inbound
static void answerChallenge(const char* cid, const char* type, const char* nonce) {
  const char* fw = (strcmp(type, "integrity") == 0) ? reportedFingerprint() : "";
  char canonical[200];
  snprintf(canonical, sizeof canonical, "%s|%s|%s|%s", NODE_ID, cid, nonce, fw);
  char sig[65]; hmacHex(canonical, sig);
  Serial.printf("{\"t\":\"resp\",\"node_id\":\"%s\",\"challenge_id\":\"%s\",\"fw\":\"%s\",\"sig\":\"%s\"}\n", NODE_ID, cid, fw, sig);
}

static void handleLine(const char* line) {
  JsonDocument doc;
  if (deserializeJson(doc, line) != DeserializationError::Ok) return;
  const char* t = doc["t"] | "";

  if (strcmp(t, "chal") == 0) {
    setStatusLeds(3);
    answerChallenge(doc["challenge_id"] | "", doc["type"] | "identity", doc["nonce"] | "");
  } else if (strcmp(t, "alarm") == 0) {
    setAlarm((doc["on"] | 0) == 1);
  } else if (strcmp(t, "led") == 0) {
    setStatusLeds(doc["code"] | 0);
  } else if (strcmp(t, "atk") == 0) {
#ifdef MALICIOUS
    const char* mode = doc["mode"] | "restore";
    if (strcmp(mode, "suppress") == 0) g_mode = SUPPRESS;
    else if (strcmp(mode, "inject") == 0) { g_mode = INJECT; g_injectTemp = doc["temp"] | 80.0f; }
    else if (strcmp(mode, "drift") == 0) { g_mode = DRIFT; g_drift = 0; }
    else { g_mode = HONEST; g_drift = 0; }
    Serial.printf("{\"t\":\"ack\",\"node_id\":\"%s\",\"mode\":\"%s\"}\n", NODE_ID, mode);
#else
    Serial.printf("{\"t\":\"ack\",\"node_id\":\"%s\",\"mode\":\"ignored\"}\n", NODE_ID);
#endif
  }
}

static char g_line[512];
static size_t g_len = 0;

static void pollSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (g_len) { g_line[g_len] = 0; handleLine(g_line); g_len = 0; }
    } else if (g_len < sizeof g_line - 1) {
      g_line[g_len++] = c;
    } else {
      g_len = 0;   // overflow: drop the line
    }
  }
}

// ---------------------------------------------------------------- arduino
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(300);
#ifdef HAS_PIR
  pinMode(PIR_PIN, INPUT);
#endif
#ifdef HAS_WATER
  analogReadResolution(12);
#endif
#ifdef HAS_ALARM
  pinMode(ALARM_PIN, OUTPUT); digitalWrite(ALARM_PIN, LOW);
#endif
#ifdef HAS_STATUS_LEDS
  pinMode(LED1_PIN, OUTPUT); pinMode(LED2_PIN, OUTPUT); setStatusLeds(0);
#endif
#ifdef HAS_TEMP_DS18B20
  temps.begin();
#endif
#ifdef HAS_TEMP_MLX
  Wire.begin(I2C_SDA, I2C_SCL);
  mlxOk = mlx.begin();
  if (!mlxOk) Serial.println("{\"t\":\"log\",\"msg\":\"MLX90614 not found on I2C; temp disabled\"}");
#endif
  loadKey();
  computeFirmwareFingerprint();
  // The boot line tells the operator this build's real fingerprint. For the honest
  // build, paste it into gateway/known_fw.json and firmware/include/secrets.h.
  Serial.printf("{\"t\":\"boot\",\"node_id\":\"%s\",\"build\":\"%s\",\"fw\":\"%s\"}\n", NODE_ID,
#ifdef MALICIOUS
                "malicious",
#else
                "honest",
#endif
                g_fw);
}

void loop() {
  static uint32_t last = 0;
  pollSerial();
  if (millis() - last >= REPORT_MS) { last = millis(); sendTelemetry(); }
  delay(5);
}
