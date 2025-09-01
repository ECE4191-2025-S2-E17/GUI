# ESP32 Integration Guide

## Overview

This guide explains how to set up and use the ESP32-based robot control system with the PyQt5 GUI interface.

## ESP32 Setup Instructions

### 1. Hardware Requirements

- **ESP32 Development Board** (ESP32-WROOM-32 or similar)
- **Motor Driver** (L298N or similar H-bridge)
- **DC Motors** (2x for left and right wheels)
- **Servo Motors** (2x for pan/tilt gimbal)
- **Battery Pack** (12V recommended)
- **Voltage Divider Circuit** (for battery monitoring)
- **Jumper Wires and Breadboard**

### 2. Wiring Diagram

```
ESP32 Pin Connections:
├── Left Motor Control
│   ├── GPIO 12 → Motor Driver IN1
│   ├── GPIO 13 → Motor Driver IN2
│   └── GPIO 14 → Motor Driver ENA (PWM)
├── Right Motor Control
│   ├── GPIO 25 → Motor Driver IN3
│   ├── GPIO 26 → Motor Driver IN4
│   └── GPIO 27 → Motor Driver ENB (PWM)
├── Servo Control
│   ├── GPIO 18 → Pan Servo Signal
│   └── GPIO 19 → Tilt Servo Signal
└── Sensors
    └── GPIO 34 → Battery Voltage (ADC)
```

### 3. Arduino IDE Setup

1. **Install ESP32 Board Package**:
   - File → Preferences
   - Add to Additional Board Manager URLs: 
     `https://dl.espressif.com/dl/package_esp32_index.json`
   - Tools → Board → Boards Manager
   - Search "ESP32" and install

2. **Install Required Libraries**:
   - Sketch → Include Library → Manage Libraries
   - Install: `ArduinoJson` (by Benoit Blanchon)
   - Install: `ESP32Servo` (by Kevin Harrington)

3. **Configure Board Settings**:
   - Board: "ESP32 Dev Module"
   - Upload Speed: "921600"
   - CPU Frequency: "240MHz (WiFi/BT)"
   - Partition Scheme: "Default 4MB with spiffs"

### 4. ESP32 Code Configuration

1. **Open** `esp32_robot_controller.ino` in Arduino IDE

2. **Configure WiFi Credentials**:
   ```cpp
   const char* ssid = "YOUR_WIFI_NETWORK";     // ⚠️ Change this
   const char* password = "YOUR_WIFI_PASSWORD"; // ⚠️ Change this
   ```

3. **Upload Code** to ESP32:
   - Connect ESP32 via USB
   - Select correct COM port
   - Click Upload button

4. **Find ESP32 IP Address**:
   - Open Serial Monitor (115200 baud)
   - Reset ESP32
   - Note the IP address displayed

## Python GUI Configuration

### 1. Update ESP32 IP Address

Edit `main.py` and change line 14:
```python
ESP32_IP = "192.168.1.100"  # ⚠️ CHANGE THIS to your ESP32's actual IP
```

### 2. Install Additional Dependencies

```bash
pip install requests==2.31.0
```

or update your environment:
```bash
conda activate ece4191
pip install -r requirements.txt
```

## Wheel Control Logic

The system implements differential drive control:

| GUI Command | Left Wheel | Right Wheel | Result |
|-------------|------------|-------------|---------|
| **Forward** | Forward | Forward | Move forward |
| **Backward** | Backward | Backward | Move backward |
| **Left Turn** | Backward | Forward | Turn left |
| **Right Turn** | Forward | Backward | Turn right |
| **Stop** | Stop | Stop | Full stop |

### Speed Control
- Speed range: 0-100% (GUI slider)
- Maps to PWM: 0-255 (ESP32 motor control)
- Both wheels use same speed for balanced movement

## API Endpoints

The ESP32 web server provides the following endpoints:

### GET `/status`
Returns ESP32 status and basic information.

**Response:**
```json
{
  "status": "online",
  "ip": "192.168.1.100",
  "uptime": 12345
}
```

### POST `/drive`
Controls individual wheel movements.

**Request:**
```json
{
  "left_wheel": {
    "direction": "forward",  // "forward", "backward", "stop"
    "speed": 75             // 0-100
  },
  "right_wheel": {
    "direction": "backward", // "forward", "backward", "stop"
    "speed": 75             // 0-100
  }
}
```

### POST `/gimbal`
Controls pan/tilt servo positions.

**Request:**
```json
{
  "pan": 25,   // -100 to 100 (left to right)
  "tilt": -10  // -100 to 100 (down to up)
}
```

### POST `/emergency_stop`
Immediately stops all motors and activates emergency mode.

### GET `/telemetry`
Returns real-time robot sensor data.

**Response:**
```json
{
  "battery_level": 85,      // 0-100%
  "left_motor_rpm": 150,    // Current RPM
  "right_motor_rpm": 148,   // Current RPM
  "suspension_height": 15.2, // cm
  "latency": 25,            // ms
  "pan_position": 90,       // degrees
  "tilt_position": 90       // degrees
}
```

## Testing and Troubleshooting

### 1. Test ESP32 Connection

1. **Check ESP32 Web Interface**:
   - Open browser and go to `http://YOUR_ESP32_IP/`
   - Should show "ESP32 Robot Controller" page

2. **Test API Endpoints**:
   ```bash
   curl http://YOUR_ESP32_IP/status
   ```

### 2. Common Issues

#### ESP32 Not Connecting to WiFi
- Verify WiFi credentials in code
- Check WiFi network (2.4GHz required, not 5GHz)
- Ensure ESP32 is in range of router

#### Python GUI Can't Connect
- Verify ESP32 IP address in `main.py`
- Check firewall settings
- Ensure both devices on same network

#### Motors Not Responding
- Check motor driver wiring
- Verify power supply connections
- Test motor driver with simple Arduino sketch first

#### Servo Jitter or Not Moving
- Check servo power supply (5V)
- Verify signal wire connections
- Test servos individually

### 3. Safety Features

- **Timeout Protection**: Motors stop if no command received for 2 seconds
- **Emergency Stop**: Immediate halt via GUI or API
- **Speed Limiting**: PWM output constrained to safe ranges
- **Voltage Monitoring**: Battery level tracking and alerts

## Network Configuration

### Static IP Setup (Optional)

For reliable connection, configure ESP32 with static IP:

```cpp
// Add to setup() function in ESP32 code
IPAddress local_IP(192, 168, 1, 100);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

if (!WiFi.config(local_IP, gateway, subnet)) {
  Serial.println("STA Failed to configure");
}
```

### Port Forwarding (Advanced)

For remote access, configure router port forwarding:
- External Port: 8080
- Internal Port: 80
- Internal IP: ESP32_IP

## Performance Optimization

### 1. Reduce Latency
- Use 2.4GHz WiFi (better range, lower latency than 5GHz)
- Position ESP32 close to WiFi router
- Reduce GUI update frequency if needed

### 2. Improve Reliability
- Add watchdog timer to ESP32 code
- Implement command acknowledgment system
- Add network reconnection logic

### 3. Battery Management
- Monitor battery voltage regularly
- Implement low-battery warnings
- Add auto-shutdown on critical battery level

## Future Enhancements

### Planned Features
- [ ] Camera streaming integration
- [ ] Encoder feedback for precise movement
- [ ] IMU integration for orientation tracking
- [ ] Autonomous navigation capabilities
- [ ] Data logging and replay functionality

### Hardware Upgrades
- [ ] Add ultrasonic sensors for obstacle detection
- [ ] Integrate GPS module for outdoor navigation
- [ ] Add LED status indicators
- [ ] Implement current sensing for motor monitoring

---

**Last Updated:** September 2025  
**Compatible Versions:** ESP32 Arduino Core v2.0+, Python 3.10.18  
**Author:** ECE4191 Team
