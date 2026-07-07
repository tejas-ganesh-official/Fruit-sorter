#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>

const char* ssid = ""; //enter wifi id
const char* password = ""; //enter wifi password
//note that ESP32, ESP32 cam AND the machine in which you run the fetch_send file must all be in the same network

String BOTtoken = ""; //insert bot token
String CHAT_ID = ""; //insert chat id

WiFiClientSecure client;

// Ultrasonic pins
#define TRIG_PIN 12
#define ECHO_PIN 14

// AI Thinker ESP32-CAM pins
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// -------- WiFi reconnect --------
void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.println("WiFi reconnecting...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println(" connected");
}

// -------- Camera --------
void startCamera() {

  camera_config_t config;

  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  config.frame_size = FRAMESIZE_UXGA;
  config.jpeg_quality = 10;

  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);

  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return;
  }

  Serial.println("Camera initialized");
}

// -------- Distance --------
float getDistance() {

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  float distance = duration * 0.034 / 2;

  return distance;
}

// -------- Send Photo --------
bool sendPhoto() {

  delay(200);

  // Flush old buffered frames
  camera_fb_t * fb = NULL;

  for (int i = 0; i < 3; i++) {

    fb = esp_camera_fb_get();

    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
    }

    delay(100);
  }

  // Capture fresh frame
  fb = esp_camera_fb_get();

  if (!fb) {
    Serial.println("Camera capture failed");
    return false;
  }

  Serial.println("Connecting to Telegram...");

  if (!client.connect("api.telegram.org", 443)) {

    Serial.println("Telegram connection failed");

    esp_camera_fb_return(fb);

    return false;
  }

  String head =
    "--ESP32\r\n"
    "Content-Disposition: form-data; name=\"chat_id\";\r\n\r\n" +
    CHAT_ID +
    "\r\n--ESP32\r\n"
    "Content-Disposition: form-data; name=\"photo\"; filename=\"esp32.jpg\"\r\n"
    "Content-Type: image/jpeg\r\n\r\n";

  String tail = "\r\n--ESP32--\r\n";

  uint32_t totalLen = fb->len + head.length() + tail.length();

  client.println("POST /bot" + BOTtoken + "/sendPhoto HTTP/1.1");
  client.println("Host: api.telegram.org");
  client.println("Content-Length: " + String(totalLen));
  client.println("Content-Type: multipart/form-data; boundary=ESP32");
  client.println();

  client.print(head);

  client.write(fb->buf, fb->len);

  client.print(tail);

  esp_camera_fb_return(fb);

  client.stop();

  Serial.println("Fresh photo sent");

  return true;
}

void setup() {

  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.println();
  Serial.println("Connecting to WiFi...");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");

  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  client.setInsecure();

  startCamera();

  delay(2000);
}

unsigned long lastTrigger = 0;

void loop() {

  ensureWiFi();

  float distance = getDistance();

  Serial.print("Distance: ");
  Serial.println(distance);

  if (distance > 1 && distance < 5) {

    // 10 second cooldown
    if (millis() - lastTrigger > 10000) {

      Serial.println("Object detected!");

      if (!sendPhoto()) {

        Serial.println("Retrying...");

        sendPhoto();
      }

      lastTrigger = millis();
    }
  }

  delay(200);
}