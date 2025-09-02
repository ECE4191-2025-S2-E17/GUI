/*
 * ESP32 Robot Controller - Arduino Sketch
 * Compatible with ECE4191 Robotic Platform Control Interface
 * 
 * ⚠️ IMPORTANT: This file should be opened and uploaded using Arduino IDE, not VS Code!
 * 
 * If you see include errors in VS Code, that's normal - this is an Arduino sketch.
 * See ARDUINO_SETUP.md for complete setup instructions.
 * 
 * This sketch creates a web server on the ESP32 that receives commands
 * from the Python GUI and controls the robot's wheels and gimbal.
 * 
 * Required Libraries (install via Arduino IDE Library Manager):
 * - WiFi (built-in with ESP32)
 * - WebServer (built-in with ESP32)
 * - ArduinoJson v6.x (by Benoit Blanchon)
 * - ESP32Servo (by Kevin Harrington)
 * 
 * Hardware Connections:
 * - Left Motor: GPIO pins 12, 13 (direction), GPIO 14 (PWM)
 * - Right Motor: GPIO pins 25, 26 (direction), GPIO 27 (PWM)
 * - Servo Pan: GPIO 18
 * - Servo Tilt: GPIO 19
 * - Battery Monitor: GPIO 34 (ADC)
 */

// ⚠️ VS Code users: These includes will show errors - this is normal!
// This file must be compiled with Arduino IDE, not VS Code.
// See ARDUINO_SETUP.md for complete instructions.

#include "esp_camera.h"  // ESP32-CAM camera library
#include <WiFi.h>        // ESP32 built-in WiFi library
#include <WebServer.h>   // ESP32 built-in web server library  
#include <ArduinoJson.h> // Install via Arduino IDE Library Manager
#include <ESP32Servo.h>  // Install via Arduino IDE Library Manager
#include "ESP_I2S.h"     // I2S audio library

// ===== WIFI CONFIGURATION =====
const char* ssid = "R12";        // ⚠️ CHANGE THIS  
const char* password = "12345678"; // ⚠️ CHANGE THIS
// ===============================

// Camera Model Configuration
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// Motor GPIO Pins
#define LEFT_MOTOR_PIN1  12
#define LEFT_MOTOR_PIN2  13
#define LEFT_MOTOR_PWM   14
#define RIGHT_MOTOR_PIN1 25
#define RIGHT_MOTOR_PIN2 26
#define RIGHT_MOTOR_PWM  27

// Servo GPIO Pins
#define SERVO_PAN_PIN    18
#define SERVO_TILT_PIN   19

// Sensor Pins
#define BATTERY_PIN      34

// Audio Configuration
#define I2S_DIN 13
#define I2S_SCK 2   // Changed from 14 to avoid conflict with motor PWM
#define I2S_WS 15
#define SAMPLING_RATE 22050
static constexpr uint32_t WIFI_BUFFER_SIZE = 4096;
static constexpr uint32_t AUDIO_BUFFER_SIZE = 1024;
static uint32_t audio_buffer[AUDIO_BUFFER_SIZE];
static int16_t audio_wifi_buffer[WIFI_BUFFER_SIZE];

// Streaming Clients
WiFiServer streamServer(81);  // Use different port for streaming
WiFiClient streamClient;
WiFiClient audioClient;

// PWM Settings
#define PWM_FREQ         1000
#define PWM_RESOLUTION   8
#define PWM_CHANNEL_LEFT 0
#define PWM_CHANNEL_RIGHT 1

// Servo Objects
Servo servoPan;
Servo servoTilt;

// I2S Audio Object
I2SClass i2s;

// Queue for drive commands
QueueHandle_t driveQueue;

// Struct for storing drive commands in queue
typedef struct {
  String dir;
  int speed;
} DriveCommand;

// Web Server
WebServer server(80);

// Robot State
struct RobotState {
  int leftWheelSpeed = 0;    // -255 to 255
  int rightWheelSpeed = 0;   // -255 to 255
  int panPosition = 90;      // 0 to 180 degrees
  int tiltPosition = 90;     // 0 to 180 degrees
  bool emergencyStop = false;
  unsigned long lastCommandTime = 0;
} robotState;

// Simple webpage for camera streaming
const char webpage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32-CAM Robot Stream</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <h1>ESP32-CAM Robot Stream</h1>
    <img src="/stream" width="640" height="480">
    <p>Use the main web interface on port 80 for robot control.</p>
</body>
</html>
)rawliteral";

void setup() {
  Serial.begin(115200);
  Serial.println("🤖 ESP32 Robot Controller Starting...");
  
  // Initialize GPIO pins
  setupMotors();
  setupServos();
  setupSensors();
  
  // Connect to WiFi
  connectToWiFi();
  
  // Start camera and streaming server
  startCamera();
  streamServer.begin();
  
  // Start I2S Audio
  Serial.println("Initializing I2S bus...");
  i2s.setPins(I2S_SCK, I2S_WS, -1, I2S_DIN);
  if (!i2s.begin(I2S_MODE_STD, SAMPLING_RATE, I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO, I2S_STD_SLOT_LEFT)) {
    Serial.println("Failed to initialize I2S bus!");
    return;
  }
  Serial.println("I2S bus initialized.");
  
  // Create queue for max. 5 drive commands
  driveQueue = xQueueCreate(5, sizeof(DriveCommand));
  
  // Setup web server routes
  setupWebServer();
  
  // Start tasks on cores 0 and 1.
  // Core 0 is for wifi/request handling/motor control,
  // core 1 is for streaming
  xTaskCreatePinnedToCore(streamTask, "StreamTask", 4096, NULL, 1, NULL, 1);
  xTaskCreatePinnedToCore(commandTask, "CommandTask", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(controlTask, "ControlTask", 4096, NULL, 2, NULL, 0);
  xTaskCreatePinnedToCore(audioBufferTask, "AudioBufferTask", 4096, NULL, 2, NULL, 0);
  
  Serial.println("✅ ESP32 Robot Controller Ready!");
  Serial.print("🌐 IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.println("📹 Video stream: http://" + WiFi.localIP().toString() + ":81/stream");
  Serial.println("🎤 Audio stream: http://" + WiFi.localIP().toString() + ":81/audio");
}

void loop() {
  server.handleClient();
  
  // Safety timeout - stop motors if no command received for 2 seconds
  if (millis() - robotState.lastCommandTime > 2000) {
    stopAllMotors();
  }
  
  // Use task delay for RTOS compatibility
  vTaskDelay(pdMS_TO_TICKS(10));
}

void setupMotors() {
  // Configure motor pins
  pinMode(LEFT_MOTOR_PIN1, OUTPUT);
  pinMode(LEFT_MOTOR_PIN2, OUTPUT);
  pinMode(RIGHT_MOTOR_PIN1, OUTPUT);
  pinMode(RIGHT_MOTOR_PIN2, OUTPUT);
  
  // Setup PWM channels
  ledcSetup(PWM_CHANNEL_LEFT, PWM_FREQ, PWM_RESOLUTION);
  ledcSetup(PWM_CHANNEL_RIGHT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(LEFT_MOTOR_PWM, PWM_CHANNEL_LEFT);
  ledcAttachPin(RIGHT_MOTOR_PWM, PWM_CHANNEL_RIGHT);
  
  stopAllMotors();
  Serial.println("✅ Motors initialized");
}

void setupServos() {
  servoPan.attach(SERVO_PAN_PIN);
  servoTilt.attach(SERVO_TILT_PIN);
  
  // Center servos
  servoPan.write(90);
  servoTilt.write(90);
  
  Serial.println("✅ Servos initialized");
}

void setupSensors() {
  pinMode(BATTERY_PIN, INPUT);
  Serial.println("✅ Sensors initialized");
}

// Camera initialization
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
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  config.frame_size = FRAMESIZE_VGA;  // VGA = 640x480, QVGA = 320x240
  config.jpeg_quality = 30;           // 0-63; Higher is lower quality
  config.fb_count = 2;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    while (true) { delay(1000); }
  }
  Serial.println("✅ Camera initialized");
}

// Audio buffer task: Handles audio streaming to client from ESP32 microphone
void audioBufferTask(void *pvParameters) {
  while (true) {
    if (!audioClient || !audioClient.connected()) {
      Serial.println("Waiting for audio client...");
      // Check for a new client connection without blocking
      audioClient = streamServer.available();
      if (!audioClient) {
        vTaskDelay(pdMS_TO_TICKS(100));  // Delay to prevent watchdog timeout
        continue;
      }
      Serial.println("Audio client connected!");
      // Disable Nagle's algorithm for lower latency
      audioClient.setNoDelay(true);
    }
    size_t bytesRead = i2s.readBytes((char *)audio_buffer, sizeof(audio_buffer));
    size_t samplesRead = bytesRead / sizeof(uint32_t);

    for (int i = 0; i < samplesRead; i++) {
      // Signed 24-bit value lives in upper 24 bits of the word
      int32_t sample24 = (int32_t)(audio_buffer[i] >> 8);
      // Downscale to 16-bit (just shift right another 8 bits, or clip)
      audio_wifi_buffer[i] = (int16_t)(sample24 >> 8);
    }

    if (samplesRead > 0 && audioClient.connected()) {
      audioClient.write((uint8_t *)audio_wifi_buffer, samplesRead * sizeof(int16_t));
    }

    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

// Stream task: Handles video streaming to client from ESP32-CAM
void streamTask(void *pvParameters) {
  while (true) {
    // Check for client requesting video
    if (streamClient && streamClient.connected()) {

      // Get frame buffer
      camera_fb_t *fb = esp_camera_fb_get();
      if (fb) {

        // Serve frame to client
        streamClient.println("--frame");
        streamClient.println("Content-Type: image/jpeg");
        streamClient.print("Content-Length: ");
        streamClient.println(fb->len);
        streamClient.println();
        streamClient.write(fb->buf, fb->len);
        streamClient.println();
        esp_camera_fb_return(fb);
      }

      vTaskDelay(pdMS_TO_TICKS(50));  // Wait 50 ms (~20 FPS)
    } else {
      // No connected client; try again later
      vTaskDelay(pdMS_TO_TICKS(100));
    }
  }
}

// Command task: Handles client requests to ESP32-CAM, including drive/gimbal commands
void commandTask(void *pvParameters) {
  while (true) {
    // Check if client is trying to connect
    WiFiClient client = streamServer.available();

    if (!client) {
      // No client has connected yet - wait 10 ms
      vTaskDelay(pdMS_TO_TICKS(10));
      continue;
    }
    // Client hasn't sent anything; wait 1 ms
    while (!client.available()) { vTaskDelay(pdMS_TO_TICKS(1)); }

    // Read message from client
    String req = client.readStringUntil('\r');
    client.readStringUntil('\n');

    // Serve homepage
    if (req.startsWith("GET / ")) {
      client.println("HTTP/1.1 200 OK");
      client.println("Content-Type: text/html");
      client.println("Connection: close");
      client.println();
      client.print(webpage);
      client.stop();

      // Serve MJPEG stream
    } else if (req.indexOf("GET /stream") >= 0) {
      streamClient = client;
      streamClient.println("HTTP/1.1 200 OK");
      streamClient.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
      streamClient.println("Connection: close");
      streamClient.println();
    } else if (req.indexOf("GET /audio") >= 0) {
      audioClient = client;
      audioClient.println("HTTP/1.1 200 OK");
      audioClient.println("Content-Type: application/octet-stream");
      audioClient.println("Connection: close");
      audioClient.println();
      // Handle drive request
    } else if (req.indexOf("GET /drive") >= 0) {
      // Initialise variables
      DriveCommand cmd;
      cmd.dir = "";
      cmd.speed = 0;

      // Read direction
      int dirIndex = req.indexOf("dir=");
      if (dirIndex > 0) {
        int amp = req.indexOf('&', dirIndex);
        cmd.dir = req.substring(dirIndex + 4, amp);
      }

      // Read speed
      int spdIndex = req.indexOf("speed=");
      if (spdIndex > 0) {
        int space = req.indexOf(' ', spdIndex);  // end of line
        cmd.speed = req.substring(spdIndex + 6, space).toInt();
      }

      // Place command in queue
      if (xQueueSend(driveQueue, &cmd, 0) == pdPASS) {
        Serial.printf("Queued drive command: dir=%s speed=%d\n",
                      cmd.dir.c_str(), cmd.speed);
      }

      // Acknowledge drive command
      client.println("HTTP/1.1 200 OK");
      client.println("Content-Type: text/plain");
      client.println("Connection: close");
      client.println();
      client.println("Drive command received");
      client.stop();

      // Didn't understand client's request
    } else {
      client.println("HTTP/1.1 404 Not Found");
      client.println("Content-Type: text/plain");
      client.println();
      client.println("Not Found");
      client.stop();
    }
  }
}

// Control task: Handles robot control using queued commands
void controlTask(void *pvParameters) {
  DriveCommand cmd;

  while (true) {
    // Check for queued command and load into cmd. Each command lasts for 100ms.
    if (xQueueReceive(driveQueue, &cmd, portMAX_DELAY)) {
      Serial.printf("Executing drive: dir=%s speed=%d\n",
                    cmd.dir.c_str(), cmd.speed);

      // Execute drive commands using existing motor control functions
      if (cmd.dir == "forward") {
        controlWheel("left", "forward", cmd.speed);
        controlWheel("right", "forward", cmd.speed);
        vTaskDelay(pdMS_TO_TICKS(100));
      } else if (cmd.dir == "backward") {
        controlWheel("left", "backward", cmd.speed);
        controlWheel("right", "backward", cmd.speed);
        vTaskDelay(pdMS_TO_TICKS(100));
      } else if (cmd.dir == "left") {
        controlWheel("left", "backward", cmd.speed);
        controlWheel("right", "forward", cmd.speed);
        vTaskDelay(pdMS_TO_TICKS(100));
      } else if (cmd.dir == "right") {
        controlWheel("left", "forward", cmd.speed);
        controlWheel("right", "backward", cmd.speed);
        vTaskDelay(pdMS_TO_TICKS(100));
      }
      // Stop motors after 100ms for failsafe
      stopAllMotors();
    }
  }
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("✅ WiFi connected!");
  } else {
    Serial.println();
    Serial.println("❌ WiFi connection failed!");
  }
}

void setupWebServer() {
  // Enable CORS for all routes
  server.on("/", HTTP_OPTIONS, handleCORS);
  server.on("/status", HTTP_OPTIONS, handleCORS);
  server.on("/drive", HTTP_OPTIONS, handleCORS);
  server.on("/gimbal", HTTP_OPTIONS, handleCORS);
  server.on("/emergency_stop", HTTP_OPTIONS, handleCORS);
  server.on("/telemetry", HTTP_OPTIONS, handleCORS);
  server.on("/stream", HTTP_OPTIONS, handleCORS);
  server.on("/audio", HTTP_OPTIONS, handleCORS);
  
  // API Routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/drive", HTTP_POST, handleDriveCommand);
  server.on("/gimbal", HTTP_POST, handleGimbalCommand);
  server.on("/emergency_stop", HTTP_POST, handleEmergencyStop);
  server.on("/telemetry", HTTP_GET, handleTelemetry);
  server.on("/stream", HTTP_GET, handleStreamRedirect);
  server.on("/audio", HTTP_GET, handleAudioRedirect);
  
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("✅ Web server started");
}

void handleCORS() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.send(200, "text/plain", "");
}

void handleRoot() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  String html = "<h1>ESP32 Robot Controller with Camera & Audio</h1>";
  html += "<p>Status: Online</p>";
  html += "<p>IP: " + WiFi.localIP().toString() + "</p>";
  html += "<p>Available endpoints:</p>";
  html += "<ul><li>/status</li><li>/drive</li><li>/gimbal</li><li>/emergency_stop</li><li>/telemetry</li><li>/stream (Video)</li><li>/audio (Audio)</li></ul>";
  html += "<p>Streaming URLs:</p>";
  html += "<ul><li>Video: http://" + WiFi.localIP().toString() + ":81/stream</li>";
  html += "<li>Audio: http://" + WiFi.localIP().toString() + ":81/audio</li></ul>";
  server.send(200, "text/html", html);
}

void handleStatus() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  DynamicJsonDocument doc(200);
  doc["status"] = "online";
  doc["ip"] = WiFi.localIP().toString();
  doc["uptime"] = millis();
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleDriveCommand() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  
  if (server.hasArg("plain")) {
    DynamicJsonDocument doc(512);
    deserializeJson(doc, server.arg("plain"));
    
    // Parse wheel commands
    String leftDirection = doc["left_wheel"]["direction"];
    int leftSpeed = doc["left_wheel"]["speed"];
    String rightDirection = doc["right_wheel"]["direction"];
    int rightSpeed = doc["right_wheel"]["speed"];
    
    // Apply wheel commands
    controlWheel("left", leftDirection, leftSpeed);
    controlWheel("right", rightDirection, rightSpeed);
    
    robotState.lastCommandTime = millis();
    
    Serial.println("🎮 Drive Command: L(" + leftDirection + "," + String(leftSpeed) + "%) R(" + rightDirection + "," + String(rightSpeed) + "%)");
    
    server.send(200, "application/json", "{\"status\":\"success\"}");
  } else {
    server.send(400, "application/json", "{\"error\":\"Invalid request\"}");
  }
}

void handleGimbalCommand() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  
  if (server.hasArg("plain")) {
    DynamicJsonDocument doc(200);
    deserializeJson(doc, server.arg("plain"));
    
    int pan = doc["pan"];
    int tilt = doc["tilt"];
    
    // Convert from -100/100 range to servo angles
    robotState.panPosition = constrain(map(pan, -100, 100, 0, 180), 0, 180);
    robotState.tiltPosition = constrain(map(tilt, -100, 100, 0, 180), 0, 180);
    
    servoPan.write(robotState.panPosition);
    servoTilt.write(robotState.tiltPosition);
    
    Serial.println("📹 Gimbal: Pan=" + String(robotState.panPosition) + "° Tilt=" + String(robotState.tiltPosition) + "°");
    
    server.send(200, "application/json", "{\"status\":\"success\"}");
  } else {
    server.send(400, "application/json", "{\"error\":\"Invalid request\"}");
  }
}

void handleEmergencyStop() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  
  robotState.emergencyStop = true;
  stopAllMotors();
  
  Serial.println("🚨 EMERGENCY STOP ACTIVATED!");
  server.send(200, "application/json", "{\"status\":\"emergency_stop_activated\"}");
}

void handleTelemetry() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  
  DynamicJsonDocument doc(512);
  
  // Read battery voltage (assuming 12V system with voltage divider)
  int batteryReading = analogRead(BATTERY_PIN);
  float batteryVoltage = (batteryReading / 4095.0) * 3.3 * 4; // Adjust multiplier for your voltage divider
  int batteryPercent = map(constrain(batteryVoltage * 10, 100, 126), 100, 126, 0, 100); // 10V-12.6V = 0-100%
  
  doc["battery_level"] = batteryPercent;
  doc["left_motor_rpm"] = abs(robotState.leftWheelSpeed) * 2;  // Simulated RPM
  doc["right_motor_rpm"] = abs(robotState.rightWheelSpeed) * 2; // Simulated RPM
  doc["suspension_height"] = 15.2; // Static value - replace with actual sensor
  doc["latency"] = 25; // Simulated latency
  doc["pan_position"] = robotState.panPosition;
  doc["tilt_position"] = robotState.tiltPosition;
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleStreamRedirect() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "Video stream available at http://" + WiFi.localIP().toString() + ":81/stream");
}

void handleAudioRedirect() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "Audio stream available at http://" + WiFi.localIP().toString() + ":81/audio");
}

void handleNotFound() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(404, "text/plain", "Endpoint not found");
}

void controlWheel(String wheel, String direction, int speed) {
  int motorSpeed = map(speed, 0, 100, 0, 255);
  
  if (wheel == "left") {
    robotState.leftWheelSpeed = (direction == "forward") ? motorSpeed : 
                               (direction == "backward") ? -motorSpeed : 0;
    
    if (direction == "forward") {
      digitalWrite(LEFT_MOTOR_PIN1, HIGH);
      digitalWrite(LEFT_MOTOR_PIN2, LOW);
    } else if (direction == "backward") {
      digitalWrite(LEFT_MOTOR_PIN1, LOW);
      digitalWrite(LEFT_MOTOR_PIN2, HIGH);
    } else {
      digitalWrite(LEFT_MOTOR_PIN1, LOW);
      digitalWrite(LEFT_MOTOR_PIN2, LOW);
      motorSpeed = 0;
    }
    
    ledcWrite(PWM_CHANNEL_LEFT, motorSpeed);
    
  } else if (wheel == "right") {
    robotState.rightWheelSpeed = (direction == "forward") ? motorSpeed : 
                                (direction == "backward") ? -motorSpeed : 0;
    
    if (direction == "forward") {
      digitalWrite(RIGHT_MOTOR_PIN1, HIGH);
      digitalWrite(RIGHT_MOTOR_PIN2, LOW);
    } else if (direction == "backward") {
      digitalWrite(RIGHT_MOTOR_PIN1, LOW);
      digitalWrite(RIGHT_MOTOR_PIN2, HIGH);
    } else {
      digitalWrite(RIGHT_MOTOR_PIN1, LOW);
      digitalWrite(RIGHT_MOTOR_PIN2, LOW);
      motorSpeed = 0;
    }
    
    ledcWrite(PWM_CHANNEL_RIGHT, motorSpeed);
  }
}

void stopAllMotors() {
  digitalWrite(LEFT_MOTOR_PIN1, LOW);
  digitalWrite(LEFT_MOTOR_PIN2, LOW);
  digitalWrite(RIGHT_MOTOR_PIN1, LOW);
  digitalWrite(RIGHT_MOTOR_PIN2, LOW);
  
  ledcWrite(PWM_CHANNEL_LEFT, 0);
  ledcWrite(PWM_CHANNEL_RIGHT, 0);
  
  robotState.leftWheelSpeed = 0;
  robotState.rightWheelSpeed = 0;
  robotState.emergencyStop = false;
}
