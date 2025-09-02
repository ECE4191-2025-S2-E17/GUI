#include "esp_camera.h"
#include <WiFi.h>
#include "ESP_I2S.h"

// Change network details as needed
const char *ssid = "R12";
const char *password = "12345678";

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// Sockets
WiFiServer server(80);
WiFiClient streamClient;
WiFiClient audioClient;

// Audio
static constexpr uint32_t WIFI_BUFFER_SIZE = 4096;
static constexpr uint32_t AUDIO_BUFFER_SIZE = 1024;
static uint32_t audio_buffer[AUDIO_BUFFER_SIZE];
static int16_t audio_wifi_buffer[WIFI_BUFFER_SIZE];
#define I2S_DIN 13
#define I2S_SCK 14
#define I2S_WS 15
#define SAMPLING_RATE 22050

// Queue to store incoming commands
QueueHandle_t driveQueue;

// Struct for storing drive commands in queue
typedef struct {
  String dir;
  int speed;
} DriveCommand;

// Camera initialisation
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
}

void audioBufferTask(void *pvParameters) {
  while (true) {
    if (!audioClient || !audioClient.connected()) {
      Serial.println("Waiting for a new client...");
      // Check for a new client connection without blocking
      audioClient = server.available();
      if (!audioClient) {
        vTaskDelay(pdMS_TO_TICKS(100));  // Delay to prevent watchdog timeout
        continue;
      }
      Serial.println("Client connected!");
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

    if (samplesRead > 0 && client.connected()) {
      audioClient.write((uint8_t *)audio_wifi_buffer, samplesRead * sizeof(int16_t));
    }

    vTaskDelay(pdMS_TO_TICKS(20));
  }
}


// Stream task: Handles video streaming to client from ESP32-CAM.
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
    WiFiClient client = server.available();

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
      streamClient = client;
      streamClient.println("HTTP/1.1 200 OK");
      streamClient.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
      streamClient.println("Connection: close");
      streamClient.println();
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

// controlTask: Handles robot control
// TODO: Discuss motor-GPIO connections with Robotics
// Currently just sends PWM output on pin 14
void controlTask(void *pvParameters) {
  DriveCommand cmd;
  const int motorPin = 14;

  while (true) {
    // Check for queued command and load into cmd. Each command lasts for 100ms.
    if (xQueueReceive(driveQueue, &cmd, portMAX_DELAY)) {
      Serial.printf("Executing drive: dir=%s speed=%d\n",
                    cmd.dir.c_str(), cmd.speed);

      // Drive forward
      if (cmd.dir == "forward") {
        ledcWrite(motorPin, cmd.speed);
        vTaskDelay(pdMS_TO_TICKS(100));

        // Drive backward
      } else if (cmd.dir == "backward") {
        ledcWrite(motorPin, cmd.speed);
        vTaskDelay(pdMS_TO_TICKS(100));

        // Drive left
      } else if (cmd.dir == "left") {
        ledcWrite(motorPin, cmd.speed);
        vTaskDelay(pdMS_TO_TICKS(100));

        // Drive right
      } else if (cmd.dir == "right") {
        ledcWrite(motorPin, cmd.speed);
        vTaskDelay(pdMS_TO_TICKS(100));
      }
      // Set PWM outputs to 0 after 100ms for failsafe.
      ledcWrite(motorPin, 0);
    }
  }
}


void setup() {
  // Baud rate: 115200
  Serial.begin(115200);

  // PWM parameters for pin 14.
  // TODO: Delete and replace with motor pin assignments
  const int motorPin = 14;
  const int freq = 5000;
  const int resolution = 8;
  ledcAttach(motorPin, freq, resolution);

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());

  // Start camera and webserver
  startCamera();
  server.begin();

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

  // Start tasks on cores 0 and 1.
  // Core 0 is for wifi/request handling/motor control,
  // core 1 is for streamingg
  xTaskCreatePinnedToCore(streamTask, "StreamTask", 4096, NULL, 1, NULL, 1);
  xTaskCreatePinnedToCore(commandTask, "CommandTask", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(controlTask, "ControlTask", 4096, NULL, 2, NULL, 0);
  xTaskCreatePinnedToCore(AudioBufferTask, "AudioBufferTask", 4096, NULL, 2, NULL, 0);
}

// Does nothing.
void loop() {
  vTaskDelay(pdMS_TO_TICKS(1000));
}
