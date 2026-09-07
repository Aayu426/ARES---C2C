// ARES camera node — OV7670 on ESP32 WROOM-32 (no PSRAM).
//
// The OV7670 has no hardware JPEG and the WROOM has no PSRAM, so we capture small
// RGB565 frames in internal RAM and software-encode each to JPEG for an MJPEG stream
// on port 81. A few frames/second, which is plenty for YOLO person detection on the
// laptop. The laptop vision service reads:  http://<ip>:81/stream
//
// Pin map matches the ARES wiring table (XCLK on GPIO4, RESET tied high, PWDN tied low).

#include <Arduino.h>
#include <WiFi.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#include "wifi_config.h"

// ---- OV7670 pin map (ARES wiring) ----
#define PWDN_GPIO_NUM   -1   // tied to GND on the board
#define RESET_GPIO_NUM  -1   // tied to 3V3 on the board
#define XCLK_GPIO_NUM    4
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y2_GPIO_NUM      5   // D0
#define Y3_GPIO_NUM     18   // D1
#define Y4_GPIO_NUM     19   // D2
#define Y5_GPIO_NUM     21   // D3
#define Y6_GPIO_NUM     36   // D4
#define Y7_GPIO_NUM     39   // D5
#define Y8_GPIO_NUM     34   // D6
#define Y9_GPIO_NUM     35   // D7
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

static httpd_handle_t g_stream_httpd = NULL;

static bool initCamera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM; config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href  = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn  = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 10000000;          // 10 MHz — OV7670 range (try 20 MHz if unstable)
  config.pixel_format = PIXFORMAT_RGB565;  // OV7670 native; we JPEG-encode in software
  config.frame_size   = FRAMESIZE_QVGA;    // 320x240 (drop to QQVGA if it won't init)
  config.fb_count     = 1;
  config.fb_location  = CAMERA_FB_IN_DRAM; // no PSRAM
  config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("{\"t\":\"log\",\"msg\":\"camera init failed 0x%x\"}\n", err);
    return false;
  }
  Serial.println("{\"t\":\"log\",\"msg\":\"camera init OK\"}");
  return true;
}

// MJPEG multipart stream
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t streamHandler(httpd_req_t* req) {
  esp_err_t res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  char part[64];

  while (true) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) { res = ESP_FAIL; break; }

    uint8_t* jpg = NULL; size_t jpg_len = 0;
    bool ok = frame2jpg(fb, 80, &jpg, &jpg_len);  // software RGB565 -> JPEG, quality 80
    esp_camera_fb_return(fb);
    if (!ok) { res = ESP_FAIL; break; }

    res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    if (res == ESP_OK) {
      size_t hlen = snprintf(part, sizeof(part), STREAM_PART, jpg_len);
      res = httpd_resp_send_chunk(req, part, hlen);
    }
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char*)jpg, jpg_len);
    free(jpg);
    if (res != ESP_OK) break;
    delay(5);
  }
  return res;
}

static void startServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;
  config.ctrl_port = 32769;
  httpd_uri_t stream_uri = { .uri = "/stream", .method = HTTP_GET, .handler = streamHandler, .user_ctx = NULL };
  if (httpd_start(&g_stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(g_stream_httpd, &stream_uri);
    Serial.println("{\"t\":\"log\",\"msg\":\"stream server on :81/stream\"}");
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  if (!initCamera()) {
    Serial.println("{\"t\":\"log\",\"msg\":\"halted: fix wiring/power and reset\"}");
    return;
  }
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("{\"t\":\"log\",\"msg\":\"joining %s\"}\n", WIFI_SSID);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) { delay(300); Serial.print("."); }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n{\"t\":\"log\",\"msg\":\"wifi failed — check hotspot/credentials\"}");
    return;
  }
  Serial.printf("\n{\"t\":\"cam\",\"ip\":\"%s\",\"stream\":\"http://%s:81/stream\"}\n",
                WiFi.localIP().toString().c_str(), WiFi.localIP().toString().c_str());
  startServer();
}

void loop() {
  delay(1000);
}
