import sys
import cv2
import time
import requests
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsDropShadowEffect
from PyQt5.QtGui import QImage, QPixmap, QColor, QKeySequence
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, Qt
from ui_main import Ui_MainWindow 
import requests

# IP_URL = "http://127.0.0.1:8080"  # Local host for now
LAPTOP_CAMERA = 0  # Use laptop camera (index 0)

# ===== ESP32 CONFIGURATION =====
# Change these settings to match your ESP32 setup
ESP32_IP = "192.168.1.100"  # CHANGE THIS to ESP32's IP address
ESP32_PORT = 80
ESP32_BASE_URL = f"http://{ESP32_IP}:{ESP32_PORT}"
# ===============================


class RobotController:
    """Handles communication with the ESP32-based robot platform"""
    
    def __init__(self, IP_URL = "http://127.0.0.1:8080"):
        self.connected = False
        self.packets_sent = 0
        self.packets_received = 0
        self.last_command_time = 0
        self.esp32_timeout = 2  # seconds
        
        # Test ESP32 connection on startup
        self.test_connection()
        
    def test_connection(self):
        """Test connection to ESP32"""
        try:
            response = requests.get(f"{ESP32_BASE_URL}/status", timeout=self.esp32_timeout)
            if response.status_code == 200:
                self.connected = True
                print("✅ ESP32 connection established")
            else:
                self.connected = False
                print("❌ ESP32 responded but with error status")
        except requests.exceptions.RequestException as e:
            self.connected = False
            print(f"❌ Failed to connect to ESP32: {e}")
    
    def send_wheel_command(self, left_wheel_direction, left_wheel_speed, right_wheel_direction, right_wheel_speed):
        """Send individual wheel commands to ESP32"""
        try:
            # Prepare wheel command data
            command_data = {
                "left_wheel": {
                    "direction": left_wheel_direction,  # "forward", "backward", "stop"
                    "speed": left_wheel_speed  # 0-100
                },
                "right_wheel": {
                    "direction": right_wheel_direction,  # "forward", "backward", "stop"
                    "speed": right_wheel_speed  # 0-100
                }
            }
            
            # Send command to ESP32
            response = requests.post(
                f"{ESP32_BASE_URL}/drive", 
                json=command_data, 
                timeout=self.esp32_timeout
            )
            
            if response.status_code == 200:
                self.packets_sent += 1
                self.last_command_time = time.time()
                print(f"🤖 Wheel Command: L({left_wheel_direction},{left_wheel_speed}%) R({right_wheel_direction},{right_wheel_speed}%)")
                return True
            else:
                print(f"❌ ESP32 command failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send command to ESP32: {e}")
            self.connected = False
            return False
        
    def send_drive_command(self, direction, speed):
        """Send drive command to robot with proper wheel mapping"""
        print(f"🎮 Drive Command: {direction} at {speed}% speed")
        
        # Map drive commands to individual wheel controls
        if direction == "forward":
            # Both wheels forward
            self.send_wheel_command("forward", speed, "forward", speed)
            
        elif direction == "backward":
            # Both wheels backward
            self.send_wheel_command("backward", speed, "backward", speed)
            
        elif direction == "left":
            # Turn left: right wheel forward, left wheel backward
            self.send_wheel_command("backward", speed, "forward", speed)
            
        elif direction == "right":
            # Turn right: left wheel forward, right wheel backward
            self.send_wheel_command("forward", speed, "backward", speed)
            
        elif direction == "stop":
            # Stop both wheels
            self.send_wheel_command("stop", 0, "stop", 0)
        
        else:
            print(f"⚠️ Unknown drive command: {direction}")
        
    def send_gimbal_command(self, pan, tilt):
        """Send gimbal control command to ESP32"""
        try:
            command_data = {
                "pan": pan,    # -100 to 100 (left to right)
                "tilt": tilt   # -100 to 100 (down to up)
            }
            
            response = requests.post(
                f"{ESP32_BASE_URL}/gimbal", 
                json=command_data, 
                timeout=self.esp32_timeout
            )
            
            if response.status_code == 200:
                self.packets_sent += 1
                print(f"📹 Gimbal Command: Pan {pan}, Tilt {tilt}")
                return True
            else:
                print(f"❌ Gimbal command failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send gimbal command: {e}")
            return False
        
    def emergency_stop(self):
        """Send emergency stop command to ESP32"""
        try:
            response = requests.post(
                f"{ESP32_BASE_URL}/emergency_stop", 
                timeout=self.esp32_timeout
            )
            
            if response.status_code == 200:
                self.packets_sent += 1
                print("🚨 EMERGENCY STOP ACTIVATED!")
                return True
            else:
                print(f"❌ Emergency stop failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send emergency stop: {e}")
            return False
        
    def get_telemetry(self):
        """Get robot telemetry data from ESP32"""
        try:
            response = requests.get(f"{ESP32_BASE_URL}/telemetry", timeout=self.esp32_timeout)
            
            if response.status_code == 200:
                self.packets_received += 1
                telemetry_data = response.json()
                
                # Return telemetry with fallback values
                return {
                    'battery_level': telemetry_data.get('battery_level', 0),
                    'left_motor_rpm': telemetry_data.get('left_motor_rpm', 0),
                    'right_motor_rpm': telemetry_data.get('right_motor_rpm', 0),
                    'suspension_height': telemetry_data.get('suspension_height', 0.0),
                    'latency': telemetry_data.get('latency', 0)
                }
            else:
                print(f"❌ Telemetry request failed: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get telemetry: {e}")
            self.connected = False
            
        # Return fallback telemetry data if ESP32 is not responding
        return {
            'battery_level': 0,
            'left_motor_rpm': 0,
            'right_motor_rpm': 0,
            'suspension_height': 0.0,
            'latency': 999
        }


class DetectionProcessor(QThread):
    """Processes object/audio detection in a separate thread"""
    
    detection_update = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = True
        
    def run(self):
        """Simulate detection processing"""
        import random
        detection_types = ["Kangaroo", "Bird", "Vehicle", "Person", "Audio Alert"]
        
        while self.running:
            time.sleep(3)  # Simulate detection every 3 seconds
            if random.random() > 0.7:  # 30% chance of detection
                detected = random.choice(detection_types)
                confidence = random.randint(70, 95)
                self.detection_update.emit(f"{detected} (Confidence: {confidence}%)")
                
    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setup UI from Designer
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Initialize robot controller
        self.robot_controller = RobotController()
        
        # Initialize detection processor
        self.detection_processor = DetectionProcessor()
        self.detection_processor.detection_update.connect(self.add_detection)
        self.detection_processor.start()

        # Video feed setup
        self.video_feed = cv2.VideoCapture(LAPTOP_CAMERA)  # Use laptop camera
        # self.video_feed = cv2.VideoCapture(IP_URL)  # Switch to this for IP camera later

        # Set up shadow effect for the video display
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.ui.Video.setGraphicsEffect(shadow)

        # Connect control signals
        self.setup_controls()

        # Create timers
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_frame)
        self.video_timer.start(30)  # 30ms = ~33 fps

        self.telemetry_timer = QTimer()
        self.telemetry_timer.timeout.connect(self.update_telemetry)
        self.telemetry_timer.start(500)  # Update every 500ms

        # Connection check timer
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_esp32_connection)
        self.connection_timer.start(5000)  # Check connection every 5 seconds

        # Initialize UI state
        self.current_speed = 50
        self.update_connection_status()
        
        # Set window properties to ensure visibility
        self.setWindowTitle("ECE4191 - Robotic Platform Control Interface")
        self.setMinimumSize(1400, 900)
        
        # Enable keyboard input
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Track key press states for continuous movement
        self.pressed_keys = set()
        
        # Make sure window appears on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.show()
        self.raise_()
        self.activateWindow()

    def setup_controls(self):
        """Connect all control signals"""
        # Drive controls
        self.ui.forwardBtn.pressed.connect(lambda: self.drive_command("forward"))
        self.ui.forwardBtn.released.connect(lambda: self.drive_command("stop"))
        self.ui.backwardBtn.pressed.connect(lambda: self.drive_command("backward"))
        self.ui.backwardBtn.released.connect(lambda: self.drive_command("stop"))
        self.ui.leftBtn.pressed.connect(lambda: self.drive_command("left"))
        self.ui.leftBtn.released.connect(lambda: self.drive_command("stop"))
        self.ui.rightBtn.pressed.connect(lambda: self.drive_command("right"))
        self.ui.rightBtn.released.connect(lambda: self.drive_command("stop"))
        self.ui.stopBtn.clicked.connect(lambda: self.drive_command("stop"))
        
        # Speed control
        self.ui.speedSlider.valueChanged.connect(self.update_speed)
        
        # Gimbal controls
        self.ui.panLeftBtn.clicked.connect(lambda: self.gimbal_command("pan_left"))
        self.ui.panRightBtn.clicked.connect(lambda: self.gimbal_command("pan_right"))
        self.ui.tiltUpBtn.clicked.connect(lambda: self.gimbal_command("tilt_up"))
        self.ui.tiltDownBtn.clicked.connect(lambda: self.gimbal_command("tilt_down"))
        self.ui.centerGimbalBtn.clicked.connect(lambda: self.gimbal_command("center"))
        
        # Emergency stop
        self.ui.emergencyStopBtn.clicked.connect(self.emergency_stop)

    def drive_command(self, direction):
        """Handle drive commands"""
        self.robot_controller.send_drive_command(direction, self.current_speed)

    def gimbal_command(self, command):
        """Handle gimbal commands"""
        gimbal_commands = {
            "pan_left": (-10, 0),
            "pan_right": (10, 0),
            "tilt_up": (0, 10),
            "tilt_down": (0, -10),
            "center": (0, 0)
        }
        pan, tilt = gimbal_commands.get(command, (0, 0))
        self.robot_controller.send_gimbal_command(pan, tilt)

    def emergency_stop(self):
        """Handle emergency stop"""
        self.robot_controller.emergency_stop()

    def update_speed(self, value):
        """Update drive speed"""
        self.current_speed = value
        self.ui.speedValueLabel.setText(f"{value}%")

    def add_detection(self, detection_text):
        """Add detection result to the list"""
        timestamp = time.strftime("%H:%M:%S")
        self.ui.detectionList.addItem(f"[{timestamp}] {detection_text}")
        
        # Keep only last 10 detections
        if self.ui.detectionList.count() > 10:
            self.ui.detectionList.takeItem(0)

    def update_frame(self):
        """Update video frame"""
        ret, frame = self.video_feed.read()
        if ret:
            # Update camera connection status
            if "Offline" in self.ui.cameraConnectionLabel.text():
                self.ui.cameraConnectionLabel.setText("Camera Feed: Online")
                self.ui.cameraConnectionLabel.setStyleSheet("color: #4CAF50;")
            
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Scale image to fit video widget
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(self.ui.Video.size(), 
                                        aspectRatioMode=1,  # Keep aspect ratio
                                        transformMode=1)    # Smooth transformation
            
            self.ui.Video.setPixmap(scaled_pixmap)
        else:
            # No video available
            if "Online" in self.ui.cameraConnectionLabel.text():
                self.ui.cameraConnectionLabel.setText("Camera Feed: Offline")
                self.ui.cameraConnectionLabel.setStyleSheet("color: #F44336;")
            self.ui.Video.setText("Camera Feed Unavailable")

    def update_telemetry(self):
        """Update telemetry display"""
        telemetry = self.robot_controller.get_telemetry()
        
        # Update motor status
        self.ui.leftMotorLabel.setText(f"Left Motor: {telemetry['left_motor_rpm']} RPM")
        self.ui.rightMotorLabel.setText(f"Right Motor: {telemetry['right_motor_rpm']} RPM")
        self.ui.suspensionHeightLabel.setText(f"Suspension Height: {telemetry['suspension_height']} cm")
        
        # Update battery
        self.ui.batteryProgress.setValue(telemetry['battery_level'])
        
        # Update communication stats
        self.ui.packetsSentLabel.setText(f"Packets Sent: {self.robot_controller.packets_sent}")
        self.ui.packetsReceivedLabel.setText(f"Packets Received: {self.robot_controller.packets_received}")
        self.ui.latencyLabel.setText(f"Latency: {telemetry['latency']} ms")

    def check_esp32_connection(self):
        """Periodically check ESP32 connection status"""
        self.robot_controller.test_connection()
        self.update_connection_status()

    def update_connection_status(self):
        """Update connection status display with ESP32 information"""
        if self.robot_controller.connected:
            self.ui.connectionStatus.setText(f"Status: Connected to ESP32 ({ESP32_IP})")
            self.ui.connectionStatus.setStyleSheet("color: #4CAF50;")
            self.ui.robotConnectionLabel.setText("Robot Connection: Online")
            self.ui.robotConnectionLabel.setStyleSheet("color: #4CAF50;")
        else:
            self.ui.connectionStatus.setText(f"Status: Disconnected from ESP32 ({ESP32_IP})")
            self.ui.connectionStatus.setStyleSheet("color: #F44336;")
            self.ui.robotConnectionLabel.setText("Robot Connection: Offline")
            self.ui.robotConnectionLabel.setStyleSheet("color: #F44336;")

    def closeEvent(self, event):
        """Clean up when closing application"""
        self.detection_processor.stop()
        self.detection_processor.wait()
        if self.video_feed.isOpened():
            self.video_feed.release()
        event.accept()

    def keyPressEvent(self, event):
        """Handle keyboard input for drive and gimbal controls"""
        key = event.key()
        
        # Add key to pressed keys set
        self.pressed_keys.add(key)
        
        # WASD for drive controls
        if key == Qt.Key_W:
            self.drive_command("forward")
            self.highlight_button(self.ui.forwardBtn, True)
        elif key == Qt.Key_A:
            self.drive_command("left")
            self.highlight_button(self.ui.leftBtn, True)
        elif key == Qt.Key_S:
            self.drive_command("backward")
            self.highlight_button(self.ui.backwardBtn, True)
        elif key == Qt.Key_D:
            self.drive_command("right")
            self.highlight_button(self.ui.rightBtn, True)
        
        # Arrow keys for gimbal controls
        elif key == Qt.Key_Left:
            self.gimbal_command("pan_left")
            self.highlight_button(self.ui.panLeftBtn, True)
        elif key == Qt.Key_Right:
            self.gimbal_command("pan_right")
            self.highlight_button(self.ui.panRightBtn, True)
        elif key == Qt.Key_Up:
            self.gimbal_command("tilt_up")
            self.highlight_button(self.ui.tiltUpBtn, True)
        elif key == Qt.Key_Down:
            self.gimbal_command("tilt_down")
            self.highlight_button(self.ui.tiltDownBtn, True)
        
        # Space for emergency stop
        elif key == Qt.Key_Space:
            self.emergency_stop()
            self.highlight_button(self.ui.emergencyStopBtn, True)
        
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Handle key release to stop continuous movement"""
        key = event.key()
        
        # Remove key from pressed keys set
        self.pressed_keys.discard(key)
        
        # Stop drive movement when keys are released
        if key in [Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D]:
            self.drive_command("stop")
            
            # Remove highlight from all drive buttons
            self.highlight_button(self.ui.forwardBtn, False)
            self.highlight_button(self.ui.leftBtn, False)
            self.highlight_button(self.ui.backwardBtn, False)
            self.highlight_button(self.ui.rightBtn, False)
        
        # Remove highlight from gimbal buttons
        elif key in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down]:
            self.highlight_button(self.ui.panLeftBtn, False)
            self.highlight_button(self.ui.panRightBtn, False)
            self.highlight_button(self.ui.tiltUpBtn, False)
            self.highlight_button(self.ui.tiltDownBtn, False)
        
        elif key == Qt.Key_Space:
            self.highlight_button(self.ui.emergencyStopBtn, False)
        
        super().keyReleaseEvent(event)

    def highlight_button(self, button, pressed):
        """Highlight button when key is pressed using CSS classes"""
        if pressed:
            button.setProperty("class", "highlighted")
            button.style().unpolish(button)
            button.style().polish(button)
        else:
            button.setProperty("class", "")
            button.style().unpolish(button)
            button.style().polish(button)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    
    # Ensure the window appears on top and is visible
    win.show()
    win.raise_()
    win.activateWindow()
    
    # Set window to appear in center of screen
    screen = app.primaryScreen()
    screen_geometry = screen.availableGeometry()
    window_geometry = win.frameGeometry()
    center_point = screen_geometry.center()
    window_geometry.moveCenter(center_point)
    win.move(window_geometry.topLeft())
    
    sys.exit(app.exec_())
