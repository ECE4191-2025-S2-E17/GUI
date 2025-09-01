# ECE4191 - Robotic Platform Control Interface with ESP32 Integration

A comprehensive GUI application for controlling and monitoring an ESP32-based robotic platform, built with PyQt5 and OpenCV. This interface provides real-time video feed, drive controls, gimbal control, object detection display, and telemetry monitoring.

## 🚀 Quick Start

### For ESP32 Integration (Recommended)

1. **Setup ESP32**: Upload Arduino sketch - see `ARDUINO_SETUP.md` 📖
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Configure IP**: Update `ESP32_IP` in `main.py` line 14
4. **Run Application**: `python main.py`

⚠️ **Arduino Setup Required**: The ESP32 sketch needs Arduino IDE - see `ARDUINO_SETUP.md` for step-by-step instructions.

## 🎮 Features

### Input Handler with ESP32 Control
- **Drive Controls**: WASD keys or GUI buttons control individual wheels
- **Differential Drive**: Smart wheel mapping for turning (left wheel backward + right wheel forward = left turn)
- **Gimbal Control**: Arrow keys or GUI buttons for camera pan/tilt operations
- **Speed Control**: Adjustable drive speed slider (0-100%) mapped to PWM (0-255)
- **Emergency Stop**: Immediate halt of all ESP32 motors

### 📹 Live Camera Feed
- Real-time video display from laptop camera or IP camera
- Automatic camera connection status monitoring
- Scalable video with maintained aspect ratio

### 🔍 Object/Audio Detection Module
- Real-time detection results display
- Timestamped detection log with confidence levels
- Ready for electrical team ML model integration

### 📊 ESP32 Telemetry Monitoring
- **Robot Connection**: ESP32 status and IP address display
- **Battery Monitoring**: Real-time voltage and percentage
- **Motor Feedback**: Individual wheel RPM monitoring
- **Communication Stats**: Packet count and latency tracking
- **Servo Positions**: Current pan/tilt angles

## 🔧 System Requirements

- **ESP32**: Development board with WiFi capability
- **Python**: 3.10.18 (tested and verified)
- **Network**: WiFi connection for ESP32 communication
- **Camera**: Built-in laptop camera or external USB camera
- **Hardware**: Motor drivers, servos, sensors (see ESP32_INTEGRATION.md)

## 📦 Installation

### Option 1: Conda Environment (Recommended)

```powershell
# Create Python 3.10.18 environment
conda create -n ece4191 python=3.10.18
conda activate ece4191

# Navigate to project and install dependencies
cd "path\to\ECE4191\GUI\pyqt5"
pip install -r requirements.txt
```

### Option 2: Virtual Environment

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## 🤖 ESP32 Robot Control

### Wheel Control Logic

The system implements differential drive control:

| GUI Command | Left Wheel | Right Wheel | Movement |
|-------------|------------|-------------|----------|
| **Forward** | ↑ Forward | ↑ Forward | Move forward |
| **Backward** | ↓ Backward | ↓ Backward | Move backward |
| **Left Turn** | ↓ Backward | ↑ Forward | Rotate left |
| **Right Turn** | ↑ Forward | ↓ Backward | Rotate right |
| **Stop** | ⏹ Stop | ⏹ Stop | Full stop |

### Quick ESP32 Setup

1. **Flash ESP32**: Upload `esp32_robot_controller.ino` 
2. **Configure WiFi**: Update SSID/password in Arduino code
3. **Find IP**: Check Serial Monitor for ESP32 IP address
4. **Update GUI**: Change `ESP32_IP` in `main.py` line 14

## 🚀 Running the Application

### ESP32-Enabled Mode:
```powershell
conda activate ece4191
cd "path\to\ECE4191\GUI\pyqt5"
python main.py
```

The GUI will automatically:
- ✅ Connect to ESP32 at configured IP
- ✅ Display connection status in header
- ✅ Enable real-time motor control
- ✅ Monitor telemetry data

## 🎯 Usage Instructions

### Keyboard Controls

| Key | Action | ESP32 Command |
|-----|--------|---------------|
| `W` | Drive Forward | Both wheels forward |
| `A` | Turn Left | Left wheel back, right wheel forward |
| `S` | Drive Backward | Both wheels backward |
| `D` | Turn Right | Left wheel forward, right wheel back |
| `↑` | Gimbal Tilt Up | Servo tilt command |
| `↓` | Gimbal Tilt Down | Servo tilt command |
| `←` | Gimbal Pan Left | Servo pan command |
| `→` | Gimbal Pan Right | Servo pan command |
| `Space` | Emergency Stop | Immediate motor halt |

### GUI Features

- **Real-time ESP32 Status**: Connection indicator in header
- **Speed Control**: Slider affects both wheels proportionally
- **Emergency Stop**: Instantly stops all ESP32 motors
- **Telemetry Display**: Live battery, RPM, and servo data
- **Auto-reconnect**: Periodic ESP32 connection testing

## 📁 File Structure

```
GUI/pyqt5/
├── main.py                      # Main application with ESP32 integration
├── ui_main.py                   # GUI layout and styling
├── esp32_robot_controller.ino   # 🤖 Arduino sketch for ESP32 (use Arduino IDE!)
├── ARDUINO_SETUP.md             # 📖 Step-by-step Arduino IDE setup guide
├── ESP32_INTEGRATION.md         # 🔧 Detailed ESP32 hardware guide
├── requirements.txt             # Python dependencies (includes requests)
├── README.md                    # This file
├── test_ui.py                   # UI testing without ESP32
└── .vscode/                     # VS Code configuration (disables .ino errors)
    ├── settings.json
    └── c_cpp_properties.json
```

## 🔧 Dependencies

```
PyQt5==5.15.9
opencv-python==4.5.5.64
numpy==1.21.6
requests==2.31.0          # ← New: For ESP32 HTTP communication
click==8.1.7
colorama==0.4.6
PyQt5_sip==12.17.0
PyQt5-Qt5==5.15.2
python-dotenv==1.0.0
```

## 🐛 Troubleshooting

### ESP32 Connection Issues
- **Can't connect**: Verify ESP32 IP in `main.py` line 14
- **Timeout errors**: Check WiFi network and firewall settings
- **No response**: Ensure ESP32 is powered and running web server

### Motor Control Problems  
- **Motors not moving**: Check ESP32 wiring and power supply
- **Erratic movement**: Verify motor driver connections
- **No wheel response**: Test ESP32 endpoints with browser/curl

### Camera Issues
- **No video feed**: Check camera permissions and availability
- **Poor quality**: Adjust resolution settings in `main.py`

### Performance Issues
- **High latency**: Reduce GUI update frequency or use closer WiFi
- **GUI freezing**: Ensure ESP32 HTTP requests don't block main thread

## 🔗 Quick Links

- **🤖 ESP32 Setup**: See `ESP32_INTEGRATION.md` for complete hardware guide
- **🧪 Testing**: Use `test_ui.py` for GUI testing without ESP32
- **🔧 Configuration**: Edit `ESP32_IP` in `main.py` for your network

## 📡 Network Configuration

### ESP32 IP Configuration
```python
# In main.py line 14:
ESP32_IP = "192.168.1.100"  # ⚠️ CHANGE THIS to your ESP32's IP
```

### Test ESP32 Connection
```bash
# Open browser and visit:
http://YOUR_ESP32_IP/status

# Or use curl:
curl http://YOUR_ESP32_IP/status
```

## 🚀 Future Enhancements

- **Camera Streaming**: Integrate ESP32-CAM for robot POV
- **Sensor Fusion**: Add ultrasonic, IMU, and encoder feedback  
- **Autonomous Mode**: GPS navigation and obstacle avoidance
- **Data Logging**: Record and replay robot movements
- **Mobile App**: Companion Android/iOS control interface

---

**Last Updated**: September 2025  
**Version**: 2.1 (ESP32 Integration)  
**Python**: 3.10.18 | **ESP32**: Arduino Core v2.0+  
**Hardware**: ESP32 + Motor Drivers + Servos


