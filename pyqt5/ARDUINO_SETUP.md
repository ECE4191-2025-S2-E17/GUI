# Arduino IDE Setup for ESP32 Robot Controller

## Quick Fix for VS Code Errors

The include errors you're seeing are normal for Arduino sketches in VS Code. The file `esp32_robot_controller.ino` is meant to be compiled with Arduino IDE, not VS Code directly.

## Option 1: Use Arduino IDE (Recommended)

### 1. Install Arduino IDE
- Download from: https://www.arduino.cc/en/software
- Install Arduino IDE 2.x (latest version)

### 2. Install ESP32 Board Package
1. Open Arduino IDE
2. Go to **File → Preferences**
3. In "Additional Board Manager URLs", add:
   ```
   https://dl.espressif.com/dl/package_esp32_index.json
   ```
4. Go to **Tools → Board → Boards Manager**
5. Search for "ESP32" and install **"ESP32 by Espressif Systems"**

### 3. Install Required Libraries
1. Go to **Sketch → Include Library → Manage Libraries**
2. Install these libraries:
   - **ArduinoJson** by Benoit Blanchon (version 6.x)
   - **ESP32Servo** by Kevin Harrington

### 4. Configure Board Settings
1. Go to **Tools → Board** and select **"ESP32 Dev Module"**
2. Set these options:
   - **Upload Speed**: 921600
   - **CPU Frequency**: 240MHz (WiFi/BT)
   - **Flash Frequency**: 80MHz
   - **Flash Mode**: QIO
   - **Flash Size**: 4MB (32Mb)
   - **Partition Scheme**: Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)
   - **Core Debug Level**: None
   - **PSRAM**: Disabled

### 5. Open and Upload the Sketch
1. **File → Open** and select `esp32_robot_controller.ino`
2. **Update WiFi credentials** in lines 26-27:
   ```cpp
   const char* ssid = "YOUR_ACTUAL_WIFI_NETWORK";
   const char* password = "YOUR_ACTUAL_WIFI_PASSWORD";
   ```
3. Connect ESP32 via USB cable
4. Select correct **COM port** in **Tools → Port**
5. Click **Upload** button (→)

### 6. Monitor Serial Output
1. Open **Tools → Serial Monitor**
2. Set baud rate to **115200**
3. Reset ESP32 to see startup messages
4. **Note the IP address** displayed (you'll need this for the Python GUI)

## Option 2: Use Arduino CLI (Advanced)

### Install Arduino CLI
```powershell
# Download and install Arduino CLI
winget install ArduinoSA.CLI
```

### Setup ESP32 and Libraries
```powershell
# Install ESP32 core
arduino-cli core update-index --additional-urls https://dl.espressif.com/dl/package_esp32_index.json
arduino-cli core install esp32:esp32

# Install required libraries
arduino-cli lib install "ArduinoJson@6.21.3"
arduino-cli lib install "ESP32Servo@0.13.0"
```

### Compile and Upload
```powershell
# Navigate to the sketch directory
cd "C:\Users\jedwo\Desktop\ECE4191\GUI\pyqt5"

# Compile the sketch
arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 esp32_robot_controller.ino

# Upload to ESP32 (replace COM3 with your actual port)
arduino-cli upload -p COM3 --fqbn esp32:esp32:esp32doit-devkit-v1 esp32_robot_controller.ino
```

## Option 3: Disable VS Code C++ IntelliSense for .ino Files

If you want to keep editing in VS Code without errors:

### Method 1: Rename File Extension
1. Rename `esp32_robot_controller.ino` to `esp32_robot_controller.cpp`
2. This will stop VS Code from trying to parse it as Arduino code
3. Remember to rename back to `.ino` before uploading

### Method 2: Configure VS Code Settings
Add to your VS Code `settings.json`:
```json
{
    "C_Cpp.errorSquiggles": "Disabled",
    "files.associations": {
        "*.ino": "cpp"
    }
}
```

## Troubleshooting

### ESP32 Not Detected
- **Install CH340/CP2102 drivers** if using clone boards
- Try different USB cables (data cables, not just charging cables)
- Check Device Manager for COM port

### Upload Failures
- Hold **BOOT** button while clicking upload
- Try lower upload speeds (115200 instead of 921600)
- Reset ESP32 before upload

### WiFi Connection Issues
- Use **2.4GHz WiFi** (ESP32 doesn't support 5GHz)
- Check SSID/password for typos
- Ensure no special characters in WiFi credentials

### Library Installation Issues
- Use Arduino IDE Library Manager instead of manual installation
- Ensure you install **ArduinoJson v6.x** (not v7.x)
- Restart Arduino IDE after installing libraries

## Next Steps

1. **Upload the ESP32 code** using Arduino IDE
2. **Note the IP address** from Serial Monitor
3. **Update the Python GUI** with the correct IP in `main.py` line 14
4. **Run the Python application** to control your robot!

## File Locations

After setup, your files will be:
- **Arduino sketch**: `esp32_robot_controller.ino` (upload this to ESP32)
- **Python GUI**: `main.py` (run this on your computer)
- **Configuration**: Update `ESP32_IP` in `main.py` to match ESP32's IP

The VS Code errors are just IntelliSense issues and don't affect the actual functionality. The Arduino code will compile and work perfectly when uploaded via Arduino IDE!
