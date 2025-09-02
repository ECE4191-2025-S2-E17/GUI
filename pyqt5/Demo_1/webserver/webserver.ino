#include "esp_camera.h"
#include "webpage.h"
#include <WiFi.h>

// Change network details as needed
const char *ssid = "Moyu";
const char *password = "tulip-kiddo-intent";

// motor setup
#define LEFT_FORWARD_PIN 12
#define LEFT_BACKWARD_PIN 13
#define RIGHT_FORWARD_PIN 15
#define RIGHT_BACKWARD_PIN 14

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// Sockets
WiFiServer server(80);
WiFiClient streamClient;

// Queue to store incoming commands
QueueHandle_t driveQueue;

// Struct for storing drive commands in queue
typedef struct {
    int lw;
    int rw;
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

    config.frame_size = FRAMESIZE_VGA; // VGA = 640x480, QVGA = 320x240
    config.jpeg_quality = 30;          // 0-63; Higher is lower quality
    config.fb_count = 2;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        while (true) {
            delay(1000);
        }
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

            vTaskDelay(pdMS_TO_TICKS(50)); // Wait 50 ms (~20 FPS)
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
        while (!client.available()) {
            vTaskDelay(pdMS_TO_TICKS(1));
        }

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
        } else if (req.indexOf("GET /drive") >= 0) {
            // Initialise variables
            DriveCommand cmd;
            int lwIndex = req.indexOf("lw=");
            if (lwIndex > 0) {
                int amp = req.indexOf('&', lwIndex);
                if (amp == -1) { // Handle case where 'lw' is the last parameter
                    amp = req.indexOf(' ', lwIndex);
                }
                cmd.lw = req.substring(lwIndex + 3, amp).toInt();
            }

            // Read right wheel speed
            int rwIndex = req.indexOf("rw=");
            if (rwIndex > 0) {
                int space = req.indexOf(' ', rwIndex); // end of line
                cmd.rw = req.substring(rwIndex + 3, space).toInt();
            }

            // Place command in queue
            if (xQueueSend(driveQueue, &cmd, 0) == pdPASS) {
                Serial.printf("Queued drive command: lw=%d rw=%d\n",
                              cmd.lw, cmd.rw);
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

    while (true) {
        // Check for queued command and load into cmd. Each command lasts for 100ms.
        if (xQueueReceive(driveQueue, &cmd, portMAX_DELAY)) {
            Serial.printf("Executing drive: lw=%d rw=%d\n",
                          cmd.lw, cmd.rw);

            // Drive forward
            if (cmd.lw > 0) {
                digitalWrite(LEFT_FORWARD_PIN, HIGH);
                digitalWrite(LEFT_BACKWARD_PIN, LOW);
            } else if (cmd.lw < 0) {
                digitalWrite(LEFT_BACKWARD_PIN, HIGH);
                digitalWrite(LEFT_FORWARD_PIN, LOW);
            } else {
                digitalWrite(LEFT_FORWARD_PIN, LOW);
                digitalWrite(LEFT_BACKWARD_PIN, LOW);
            }
            if (cmd.rw > 0) {
                digitalWrite(RIGHT_FORWARD_PIN, HIGH);
                digitalWrite(RIGHT_BACKWARD_PIN, LOW);
            } else if (cmd.rw < 0) {
                digitalWrite(RIGHT_BACKWARD_PIN, HIGH);
                digitalWrite(RIGHT_FORWARD_PIN, LOW);
            } else {
                digitalWrite(RIGHT_FORWARD_PIN, LOW);
                digitalWrite(RIGHT_BACKWARD_PIN, LOW);
            }
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}

void setup() {
    // Baud rate: 115200
    Serial.begin(115200);

    // PWM parameters for pin 14.
    // TODO: Delete and replace with motor pin assignments
    pinMode(LEFT_BACKWARD_PIN, OUTPUT);
    pinMode(LEFT_FORWARD_PIN, OUTPUT);
    pinMode(RIGHT_BACKWARD_PIN, OUTPUT);
    pinMode(RIGHT_FORWARD_PIN, OUTPUT);

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

    // Create queue for max. 5 drive commands
    driveQueue = xQueueCreate(5, sizeof(DriveCommand));

    // Start tasks on cores 0 and 1.
    // Core 0 is for wifi/request handling/motor control,
    // core 1 is for streamingg
    xTaskCreatePinnedToCore(streamTask, "StreamTask", 4096, NULL, 1, NULL, 1);
    xTaskCreatePinnedToCore(commandTask, "CommandTask", 4096, NULL, 1, NULL, 0);
    xTaskCreatePinnedToCore(controlTask, "ControlTask", 4096, NULL, 2, NULL, 0);
}

// Does nothing.
void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}
