#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

// ===== WiFi =====
const char* ssid = ""; //wifi id
const char* password = ""; //wifi password

// ===== Server =====
WebServer server(80);

// ===== Servos =====
Servo servo1;
Servo servo2;

const int SERVO1_PIN = 18;
const int SERVO2_PIN = 19;

// ===== Handler =====
void handleData() {
  if (server.hasArg("label") && server.hasArg("conf")) {

    String label = server.arg("label");
    String conf = server.arg("conf");

    Serial.print("Prediction: ");
    Serial.print(label);
    Serial.print(" | Confidence: ");
    Serial.println(conf);

    // ===== SERVO LOGIC =====
    if (label == "old" || label == "damaged") {
      Serial.println("Activating Servo 1 → 270°");
      servo1.write(0);
      delay(4000);
      servo1.write(90);  // return to home

    } else if (label == "ripe" || label == "unripe") {
      Serial.println("Activating Servo 2 → 270°");
      servo2.write(90);
      delay(4000);
      servo2.write(0);  // return to home
    }

    server.send(200, "text/plain", "OK");

  } else {
    Serial.println("Invalid request");
    server.send(400, "text/plain", "Missing params");
  }
}

void setup() {
  Serial.begin(115200);

  // ===== Servo Setup =====
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo1.write(90);
  servo2.write(0);

  // ===== WiFi =====
  WiFi.begin(ssid, password);
  Serial.print("Connecting");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.println(WiFi.localIP());

  server.on("/data", handleData);
  server.begin();

  Serial.println("Server started");
}

void loop() {
  server.handleClient();
}