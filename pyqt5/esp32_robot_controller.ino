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

#include <WiFi.h>        // ESP32 built-in WiFi library
#include <WebServer.h>   // ESP32 built-in web server library  
#include <ArduinoJson.h> // Install via Arduino IDE Library Manager
#include <ESP32Servo.h>  // Install via Arduino IDE Library Manager

// ===== WIFI CONFIGURATION =====
const char* ssid = "YOUR_WIFI_SSID";        // ⚠️ CHANGE THIS
const char* password = "YOUR_WIFI_PASSWORD"; // ⚠️ CHANGE THIS
// ===============================

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

// PWM Settings
#define PWM_FREQ         1000
#define PWM_RESOLUTION   8
#define PWM_CHANNEL_LEFT 0
#define PWM_CHANNEL_RIGHT 1

// Servo Objects
Servo servoPan;
Servo servoTilt;

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

void setup() {
  Serial.begin(115200);
  Serial.println("🤖 ESP32 Robot Controller Starting...");
  
  // Initialize GPIO pins
  setupMotors();
  setupServos();
  setupSensors();
  
  // Connect to WiFi
  connectToWiFi();
  
  // Setup web server routes
  setupWebServer();
  
  Serial.println("✅ ESP32 Robot Controller Ready!");
  Serial.print("🌐 IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  server.handleClient();
  
  // Safety timeout - stop motors if no command received for 2 seconds
  if (millis() - robotState.lastCommandTime > 2000) {
    stopAllMotors();
  }
  
  delay(10);
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
  
  // API Routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/drive", HTTP_POST, handleDriveCommand);
  server.on("/gimbal", HTTP_POST, handleGimbalCommand);
  server.on("/emergency_stop", HTTP_POST, handleEmergencyStop);
  server.on("/telemetry", HTTP_GET, handleTelemetry);
  
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
  String html = "<h1>ESP32 Robot Controller</h1>";
  html += "<p>Status: Online</p>";
  html += "<p>IP: " + WiFi.localIP().toString() + "</p>";
  html += "<p>Available endpoints:</p>";
  html += "<ul><li>/status</li><li>/drive</li><li>/gimbal</li><li>/emergency_stop</li><li>/telemetry</li></ul>";
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
