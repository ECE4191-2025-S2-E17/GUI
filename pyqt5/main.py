import sys
import cv2
import time
import requests
import json
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsDropShadowEffect
from PyQt5.QtGui import QImage, QPixmap, QColor, QKeySequence
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, Qt
from ui_main import Ui_MainWindow 
import requests

# ===== CAMERA CONFIGURATION =====
# Choose camera source: "esp32", "ip_camera", or "local"
CAMERA_SOURCE = "esp32"  # Changed to use ESP32 since it's working

# ESP32-CAM Configuration
ESP32_IP = "172.20.10.2"  # ESP32's actual IP address
ESP32_PORT = 80
ESP32_CAMERA_URL = f"http://{ESP32_IP}/stream"
ESP32_BASE_URL = f"http://{ESP32_IP}:{ESP32_PORT}"

# Alternative ESP32 IP addresses to try (in case DHCP assigned different IP)
ESP32_FALLBACK_IPS = [
    "192.168.5.129", # Current ESP32 IP
    "192.168.4.1",   # Default ESP32 AP mode IP  
    "192.168.1.1",   # Common ESP32 AP mode IP
    "192.168.1.100", # Common router-assigned IP range
    "192.168.1.101",
    "192.168.1.102",
    "192.168.0.100", # Another common router IP range
    "192.168.0.101",
    "192.168.0.102"
]

# IP Camera Configuration 
IP_CAMERA_URL = f"http://{ESP32_IP}/stream"  # Use ESP32 stream for now
# Common IP camera URL formats:
# "http://192.168.1.100:8080/video_feed"  # Phone camera apps  
# "http://192.168.1.100/mjpg/video.mjpg"  # MJPEG cameras
# "rtsp://192.168.1.100:554/stream"       # RTSP cameras
# ===================================


class IPCamera:
    """Handles IP camera streams with multiple format support"""
    
    def __init__(self, stream_url):
        self.stream_url = stream_url
        self.video = None
        self.connected = False
        self.session = requests.Session()
        self.session.timeout = 5
        self.last_frame = None
        
        # Try to connect using OpenCV first (works well for RTSP and some HTTP streams)
        self.connect_opencv()
        
        # If OpenCV fails, we'll fall back to HTTP requests method
        if not self.connected:
            self.connect_http()
    
    def connect_opencv(self):
        """Try to connect using OpenCV VideoCapture (good for RTSP, some HTTP)"""
        try:
            # Set OpenCV environment variables for better HTTP/RTSP support
            import os
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"
            
            self.video = cv2.VideoCapture(self.stream_url)
            if self.video.isOpened():
                # Test if we can actually read a frame
                ret, frame = self.video.read()
                if ret and frame is not None:
                    self.connected = True
                    self.last_frame = frame
                    print(f"✅ Connected to IP camera via OpenCV: {self.stream_url}")
                    return
                else:
                    self.video.release()
                    self.video = None
        except Exception as e:
            print(f"OpenCV connection failed: {e}")
            if self.video:
                self.video.release()
                self.video = None
    
    def connect_http(self):
        """Try to connect using HTTP requests (good for MJPEG streams)"""
        try:
            # Test HTTP connection
            response = self.session.get(self.stream_url, timeout=3, stream=True)
            if response.status_code == 200:
                print(f"✅ Connected to IP camera via HTTP: {self.stream_url}")
                self.connected = True
            else:
                print(f"❌ HTTP connection failed: {response.status_code}")
        except Exception as e:
            print(f"❌ HTTP connection failed: {e}")
    
    def get_frame(self):
        """Get frame from IP camera"""
        # Try OpenCV method first
        if self.video and self.video.isOpened():
            ret, frame = self.video.read()
            if ret and frame is not None:
                self.connected = True
                self.last_frame = frame
                return frame
            else:
                # OpenCV failed, try to reconnect
                self.video.release()
                self.video = None
                self.connect_opencv()
        
        # Try HTTP method for MJPEG streams
        if not self.video:
            try:
                response = self.session.get(self.stream_url, timeout=2, stream=True)
                if response.status_code == 200:
                    # For MJPEG streams, we need to parse the multipart response
                    content_type = response.headers.get('content-type', '')
                    if 'multipart' in content_type:
                        # This is a basic MJPEG parser - might need adjustment for specific cameras
                        boundary = content_type.split('boundary=')[-1]
                        for chunk in response.iter_content(chunk_size=1024):
                            if b'\xff\xd8' in chunk and b'\xff\xd9' in chunk:
                                # Found JPEG start and end markers
                                start = chunk.find(b'\xff\xd8')
                                end = chunk.find(b'\xff\xd9', start) + 2
                                if start != -1 and end != -1:
                                    jpeg_data = chunk[start:end]
                                    frame = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
                                    if frame is not None:
                                        self.connected = True
                                        self.last_frame = frame
                                        return frame
                                break
                    else:
                        # Try to decode as single image
                        img_array = np.frombuffer(response.content[:50000], np.uint8)  # Limit size
                        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        if frame is not None:
                            self.connected = True
                            self.last_frame = frame
                            return frame
            except Exception as e:
                print(f"HTTP frame capture error: {e}")
                self.connected = False
        
        # Return last known frame if available
        return self.last_frame
    
    def isOpened(self):
        """Check if camera connection is available"""
        return self.connected
    
    def release(self):
        """Clean up camera resources"""
        if self.video:
            self.video.release()
        self.session.close()


class ESP32Camera:
    """Handles ESP32-CAM stream using the webserver.ino endpoints"""
    
    def __init__(self, stream_url=None):
        self.stream_url = stream_url or ESP32_CAMERA_URL
        self.session = requests.Session()
        self.session.timeout = 3
        self.connected = False
        self.last_frame = None
        self.video_capture = None
        self.esp32_ip = ESP32_IP
        self.esp32_base_url = ESP32_BASE_URL
        
        # Find and connect to ESP32
        self.find_and_connect()
        
    def find_and_connect(self):
        """Try to find ESP32 on network and establish connection"""
        print("🔍 Searching for ESP32-CAM...")
        
        # Try the configured IP first
        if self.test_esp32_connection(self.esp32_ip):
            self.setup_connection(self.esp32_ip)
            return
            
        # If configured IP fails, try fallback IPs
        print(f"❌ ESP32 not found at {self.esp32_ip}, trying fallback IPs...")
        for fallback_ip in ESP32_FALLBACK_IPS:
            if fallback_ip != self.esp32_ip:  # Skip if same as configured IP
                if self.test_esp32_connection(fallback_ip):
                    print(f"✅ ESP32 found at {fallback_ip}")
                    self.setup_connection(fallback_ip)
                    return
                    
        print("❌ ESP32-CAM not found on any attempted IP addresses")
        
    def test_esp32_connection(self, ip):
        """Test if ESP32 is accessible at given IP"""
        try:
            test_url = f"http://{ip}/"
            response = self.session.get(test_url, timeout=2)
            # ESP32 webserver returns webpage content on root path
            if response.status_code == 200 and len(response.text) > 100:
                return True
        except:
            pass
        return False
        
    def setup_connection(self, ip):
        """Setup connection to ESP32 at given IP"""
        self.esp32_ip = ip
        self.esp32_base_url = f"http://{ip}:80"
        self.stream_url = f"http://{ip}/stream"
        
        # Try to connect using OpenCV first (often works well with MJPEG streams)
        self.try_opencv_connection()
        
    def try_opencv_connection(self):
        """Try to connect using OpenCV VideoCapture for MJPEG stream with optimizations"""
        try:
            print(f"🎥 Connecting to ESP32 stream: {self.stream_url}")
            self.video_capture = cv2.VideoCapture(self.stream_url)
            
            if self.video_capture.isOpened():
                # Optimize OpenCV settings for better performance
                self.video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize latency
                self.video_capture.set(cv2.CAP_PROP_FPS, 30)  # Set target FPS
                
                # Test if we can read a frame
                ret, frame = self.video_capture.read()
                if ret and frame is not None:
                    self.connected = True
                    self.last_frame = frame
                    print("✅ ESP32-CAM stream connected via OpenCV with optimizations")
                    return True
                else:
                    self.video_capture.release()
                    self.video_capture = None
                    
        except Exception as e:
            print(f"OpenCV connection failed: {e}")
            if self.video_capture:
                self.video_capture.release()
                self.video_capture = None
        
        return False
        
    def get_frame(self):
        """Get a single frame from ESP32-CAM stream with optimized performance"""
        # Try OpenCV method first (continuous MJPEG stream) - most efficient
        if self.video_capture and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret and frame is not None:
                self.connected = True
                self.last_frame = frame
                return frame
            else:
                # OpenCV failed, try to reconnect
                print("📹 OpenCV stream interrupted, attempting reconnect...")
                self.video_capture.release()
                self.video_capture = None
                if self.try_opencv_connection():
                    ret, frame = self.video_capture.read()
                    if ret and frame is not None:
                        return frame
        
        # Fallback: Try to parse MJPEG stream manually (less efficient but more reliable)
        try:
            response = self.session.get(self.stream_url, timeout=1, stream=True)  # Reduced timeout for faster response
            if response.status_code == 200:
                # Read and parse MJPEG stream more efficiently
                buffer = b""
                max_frame_size = 100000  # Limit frame size for performance
                
                for chunk in response.iter_content(chunk_size=2048):  # Larger chunks for efficiency
                    buffer += chunk
                    
                    # Look for JPEG frame boundaries
                    start_marker = buffer.find(b'\xff\xd8')  # JPEG start
                    if start_marker == -1:
                        continue
                        
                    end_marker = buffer.find(b'\xff\xd9', start_marker)  # JPEG end
                    
                    if end_marker != -1:
                        # Extract complete JPEG frame
                        jpeg_data = buffer[start_marker:end_marker+2]
                        
                        # Decode frame with error handling
                        try:
                            frame = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
                            if frame is not None and frame.size > 0:
                                self.connected = True
                                self.last_frame = frame
                                return frame
                        except Exception as e:
                            print(f"Frame decode error: {e}")
                        
                        # Remove processed frame from buffer
                        buffer = buffer[end_marker+2:]
                        
                    # Prevent buffer from growing too large (performance optimization)
                    if len(buffer) > max_frame_size:
                        # Keep only the most recent data
                        recent_start = max(0, len(buffer) - max_frame_size//2)
                        buffer = buffer[recent_start:]
                        
                    # Quick exit after finding first valid frame
                    if len(jpeg_data) > 1000:  # Reasonable frame size check
                        break
                        
        except Exception as e:
            print(f"ESP32 stream error: {e}")
            self.connected = False
            
        # Return last known frame if available (maintains smoother video during brief interruptions)
        if self.last_frame is not None:
            return self.last_frame
            
        return None
    
    def isOpened(self):
        """Check if camera connection is available"""
        return self.connected
    
    def release(self):
        """Clean up camera resources"""
        if self.video_capture:
            self.video_capture.release()
        self.session.close()
        
    def get_esp32_ip(self):
        """Get the current ESP32 IP address"""
        return self.esp32_ip
            
        # Return last known frame if available
        return self.last_frame
    
    def isOpened(self):
        """Check if camera connection is available"""
        return self.connected
    
    def release(self):
        """Clean up camera resources"""
        if self.video_capture:
            self.video_capture.release()
        self.session.close()


class LocalCamera:
    """Fallback to local camera if ESP32-CAM is not available"""
    
    def __init__(self, source=0):
        self.video = cv2.VideoCapture(source)
        self.connected = self.video.isOpened()
        
    def get_frame(self):
        """Get frame from local camera"""
        if self.video.isOpened():
            ret, frame = self.video.read()
            if ret:
                self.connected = True
                return frame
        self.connected = False
        return None
        
    def isOpened(self):
        return self.connected
        
    def release(self):
        if self.video.isOpened():
            self.video.release()


class RobotController:
    """Handles communication with the ESP32-based robot platform"""
    
    def __init__(self):
        self.connected = False
        self.packets_sent = 0
        self.packets_received = 0
        self.last_command_time = 0
        self.esp32_timeout = 3  # seconds
        self.esp32_ip = ESP32_IP
        self.esp32_base_url = ESP32_BASE_URL
        
        # Find ESP32 and test connection on startup
        self.find_and_test_connection()
        
    def find_and_test_connection(self):
        """Find ESP32 on network and test connection"""
        print("🔍 Searching for ESP32 robot controller...")
        
        # Try the configured IP first
        if self.test_esp32_connection(self.esp32_ip):
            self.setup_connection(self.esp32_ip)
            return
            
        # If configured IP fails, try fallback IPs
        for fallback_ip in ESP32_FALLBACK_IPS:
            if fallback_ip != self.esp32_ip:
                if self.test_esp32_connection(fallback_ip):
                    print(f"✅ ESP32 robot found at {fallback_ip}")
                    self.setup_connection(fallback_ip)
                    return
                    
        print("❌ ESP32 robot controller not found")
        
    def test_esp32_connection(self, ip):
        """Test if ESP32 is accessible at given IP"""
        try:
            test_url = f"http://{ip}/"
            response = requests.get(test_url, timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        return False
        
    def setup_connection(self, ip):
        """Setup connection to ESP32 at given IP"""
        self.esp32_ip = ip
        self.esp32_base_url = f"http://{ip}:80"
        self.connected = True
        print(f"✅ ESP32 robot controller connected at {ip}")
    
    def send_wheel_command(self, left_wheel_direction, left_wheel_speed, right_wheel_direction, right_wheel_speed):
        """Send individual wheel commands to ESP32 using webserver.ino format"""
        try:
            # Convert direction and speed to the format expected by webserver.ino
            # webserver.ino expects lw and rw parameters with signed integers
            # Positive = forward, Negative = backward, 0 = stop
            
            left_wheel_value = 0
            right_wheel_value = 0
            
            if left_wheel_direction == "forward":
                left_wheel_value = left_wheel_speed
            elif left_wheel_direction == "backward":
                left_wheel_value = -left_wheel_speed
            else:  # stop
                left_wheel_value = 0
                
            if right_wheel_direction == "forward":
                right_wheel_value = right_wheel_speed
            elif right_wheel_direction == "backward":
                right_wheel_value = -right_wheel_speed
            else:  # stop
                right_wheel_value = 0
            
            # Send command to ESP32 using GET request with parameters
            # Format: /drive?lw=<left_wheel>&rw=<right_wheel>
            drive_url = f"{self.esp32_base_url}/drive?lw={left_wheel_value}&rw={right_wheel_value}"
            
            response = requests.get(drive_url, timeout=self.esp32_timeout)
            
            if response.status_code == 200:
                self.packets_sent += 1
                self.last_command_time = time.time()
                self.connected = True
                print(f"🤖 Drive Command: lw={left_wheel_value}, rw={right_wheel_value}")
                return True
            else:
                print(f"❌ ESP32 drive command failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send drive command to ESP32: {e}")
            self.connected = False
            return False
    
    def send_drive_command(self, direction, speed):
        """Send drive command (both wheels same direction/speed)"""
        return self.send_wheel_command(direction, speed, direction, speed)
    
    def send_turn_command(self, turn_direction, speed):
        """Send turn command (wheels in opposite directions)"""
        if turn_direction == "left":
            # Left turn: left wheel forward, right wheel backward
            return self.send_wheel_command("forward", speed, "backward", speed)
        elif turn_direction == "right":
            # Right turn: right wheel forward, left wheel backward
            return self.send_wheel_command("backward", speed, "forward", speed)
        else:
            return self.send_wheel_command("stop", 0, "stop", 0)
    
    def stop_robot(self):
        """Stop both wheels"""
        return self.send_wheel_command("stop", 0, "stop", 0)
        
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
            # Turn left: left wheel forward, right wheel backward
            self.send_wheel_command("forward", speed, "backward", speed)
            
        elif direction == "right":
            # Turn right: right wheel forward, left wheel backward
            self.send_wheel_command("backward", speed, "forward", speed)
            
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
        
        self.detection_processor = DetectionProcessor()
        self.detection_processor.detection_update.connect(self.add_detection)
        self.detection_processor.start()

        # Video feed setup - choose camera source based on configuration
        self.esp32_camera = None
        self.ip_camera = None
        self.local_camera = LocalCamera(0)  # Always have local camera as fallback
        self.current_camera = None
        
        # Initialize cameras based on configuration
        if CAMERA_SOURCE == "ip_camera":
            self.ip_camera = IPCamera(IP_CAMERA_URL)
        elif CAMERA_SOURCE == "esp32":
            self.esp32_camera = ESP32Camera()  # Auto-discovery enabled
        # local camera is always available as fallback
        
        self.setup_camera()

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
        self.video_timer.start(33)  # 33ms = ~30 fps for smoother, more stable video
        
        # Add frame rate tracking
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        self.target_fps = 30
        self.frame_skip_counter = 0
        self.performance_adjustment_timer = QTimer()
        self.performance_adjustment_timer.timeout.connect(self.adjust_performance)
        self.performance_adjustment_timer.start(5000)  # Check performance every 5 seconds

        self.telemetry_timer = QTimer()
        self.telemetry_timer.timeout.connect(self.update_telemetry)
        self.telemetry_timer.start(250)  # Update every 250ms for more responsive telemetry

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

    def setup_camera(self):
        """Setup camera source based on configuration"""
        print("🎥 Setting up camera...")
        
        # Try primary camera source first
        if CAMERA_SOURCE == "ip_camera" and self.ip_camera:
            test_frame = self.ip_camera.get_frame()
            if test_frame is not None:
                self.current_camera = self.ip_camera
                print("✅ Using IP Camera")
                return
                
        elif CAMERA_SOURCE == "esp32" and self.esp32_camera:
            test_frame = self.esp32_camera.get_frame()
            if test_frame is not None:
                self.current_camera = self.esp32_camera
                print("✅ Using ESP32-CAM")
                return
                
        elif CAMERA_SOURCE == "local":
            test_frame = self.local_camera.get_frame()
            if test_frame is not None:
                self.current_camera = self.local_camera
                print("✅ Using Local Camera")
                return
        
        # Fallback sequence: try other available cameras
        print(f"❌ Primary camera source '{CAMERA_SOURCE}' failed, trying alternatives...")
        
        # Try IP camera if not primary
        if CAMERA_SOURCE != "ip_camera" and self.ip_camera:
            test_frame = self.ip_camera.get_frame()
            if test_frame is not None:
                self.current_camera = self.ip_camera
                print("✅ Using IP Camera (fallback)")
                return
        
        # Try ESP32-CAM if not primary  
        if CAMERA_SOURCE != "esp32" and self.esp32_camera:
            test_frame = self.esp32_camera.get_frame()
            if test_frame is not None:
                self.current_camera = self.esp32_camera
                print("✅ Using ESP32-CAM (fallback)")
                return
                
        # Try local camera if not primary
        if CAMERA_SOURCE != "local":
            test_frame = self.local_camera.get_frame()
            if test_frame is not None:
                self.current_camera = self.local_camera
                print("✅ Using Local Camera (fallback)")
                return
            
        print("❌ No camera available")
        self.current_camera = None

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
        """Update video frame with performance optimization"""
        current_time = time.time()
        
        # Calculate FPS
        self.frame_count += 1
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            
        # Adaptive frame skipping for performance
        if self.current_fps < self.target_fps * 0.8:  # If FPS drops below 80% of target
            self.frame_skip_counter += 1
            if self.frame_skip_counter < 2:  # Skip every 2nd frame if performance is poor
                return
            self.frame_skip_counter = 0
        
        if self.current_camera is None:
            # Try to reconnect cameras
            self.setup_camera()
            if self.current_camera is None:
                self.ui.Video.setText("No Camera Available")
                self.ui.cameraConnectionLabel.setText("Camera Feed: No Camera")
                self.ui.cameraConnectionLabel.setStyleSheet("color: #F44336;")
                return
        
        frame = self.current_camera.get_frame()
        if frame is not None:
            # Rotate frame 90 degrees anticlockwise
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            # Update camera connection status only when needed
            current_status = self.ui.cameraConnectionLabel.text()
            if "Offline" in current_status or "No Camera" in current_status:
                if isinstance(self.current_camera, IPCamera):
                    camera_type = "IP Camera"
                elif isinstance(self.current_camera, ESP32Camera):
                    camera_type = "ESP32-CAM"
                else:
                    camera_type = "Local Camera"
                    
                self.ui.cameraConnectionLabel.setText(f"Camera Feed: Online ({camera_type}) - {self.current_fps:.1f} FPS")
                self.ui.cameraConnectionLabel.setStyleSheet("color: #4CAF50;")
            elif "Online" in current_status and self.frame_count % 30 == 0:  # Update FPS every 30 frames
                # Extract camera type from existing text
                if "ESP32-CAM" in current_status:
                    camera_type = "ESP32-CAM"
                elif "IP Camera" in current_status:
                    camera_type = "IP Camera"
                else:
                    camera_type = "Local Camera"
                self.ui.cameraConnectionLabel.setText(f"Camera Feed: Online ({camera_type}) - {self.current_fps:.1f} FPS")
            
            # Optimize frame processing
            # Resize frame if it's too large for better performance
            height, width = frame.shape[:2]
            if width > 800 or height > 600:
                scale_factor = min(800/width, 600/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            # Convert BGR to RGB for Qt display
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Scale image to fit video widget with optimized transformation
            pixmap = QPixmap.fromImage(qt_image)
            video_size = self.ui.Video.size()
            
            # Only scale if necessary
            if pixmap.size() != video_size:
                scaled_pixmap = pixmap.scaled(video_size, 
                                            aspectRatioMode=Qt.KeepAspectRatio,  
                                            transformMode=Qt.FastTransformation)  # Use fast transformation for better performance
            else:
                scaled_pixmap = pixmap
            
            self.ui.Video.setPixmap(scaled_pixmap)
        else:
            # No video available - try to reconnect or switch cameras
            if isinstance(self.current_camera, IPCamera):
                # IP camera failed, try other cameras
                print("📹 IP Camera failed, trying alternatives...")
                if self.esp32_camera:
                    test_frame = self.esp32_camera.get_frame()
                    if test_frame is not None:
                        self.current_camera = self.esp32_camera
                        print("✅ Switched to ESP32-CAM")
                        return
                        
                test_frame = self.local_camera.get_frame()
                if test_frame is not None:
                    self.current_camera = self.local_camera
                    print("✅ Switched to local camera")
                    return
                    
            elif isinstance(self.current_camera, ESP32Camera):
                # ESP32-CAM failed, try other cameras
                print("📹 ESP32-CAM failed, trying alternatives...")
                if self.ip_camera:
                    test_frame = self.ip_camera.get_frame()
                    if test_frame is not None:
                        self.current_camera = self.ip_camera
                        print("✅ Switched to IP camera")
                        return
                        
                test_frame = self.local_camera.get_frame()
                if test_frame is not None:
                    self.current_camera = self.local_camera
                    print("✅ Switched to local camera")
                    return
            
            # Update UI to show camera offline
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
        if not self.robot_controller.connected:
            # Try to reconnect
            self.robot_controller.find_and_test_connection()
        self.update_connection_status()

    def update_connection_status(self):
        """Update connection status display with ESP32 information"""
        if self.robot_controller.connected:
            esp32_ip = self.robot_controller.esp32_ip
            self.ui.connectionStatus.setText(f"Status: Connected to ESP32 ({esp32_ip})")
            self.ui.connectionStatus.setStyleSheet("color: #4CAF50;")
            self.ui.robotConnectionLabel.setText("Robot Connection: Online")
            self.ui.robotConnectionLabel.setStyleSheet("color: #4CAF50;")
            
            # Update global ESP32 URL if IP changed
            global ESP32_IP, ESP32_BASE_URL, ESP32_CAMERA_URL
            if esp32_ip != ESP32_IP:
                ESP32_IP = esp32_ip
                ESP32_BASE_URL = f"http://{esp32_ip}:80"
                ESP32_CAMERA_URL = f"http://{esp32_ip}/stream"
                print(f"🔄 Updated ESP32 IP to: {esp32_ip}")
        else:
            self.ui.connectionStatus.setText(f"Status: Searching for ESP32...")
            self.ui.connectionStatus.setStyleSheet("color: #F44336;")
            self.ui.robotConnectionLabel.setText("Robot Connection: Offline")
            self.ui.robotConnectionLabel.setStyleSheet("color: #F44336;")

    def adjust_performance(self):
        """Dynamically adjust video performance based on current FPS"""
        if self.current_fps > 0:
            if self.current_fps < self.target_fps * 0.7:  # If FPS is below 70% of target
                # Reduce frame rate to improve stability
                new_interval = int(self.video_timer.interval() * 1.2)  # Increase interval by 20%
                if new_interval <= 50:  # Don't go below 20 FPS
                    self.video_timer.setInterval(new_interval)
                    print(f"📊 Performance: Adjusted frame interval to {new_interval}ms for stability")
            elif self.current_fps > self.target_fps * 1.1 and self.video_timer.interval() > 25:  # If FPS is above 110% of target
                # Increase frame rate if performance allows
                new_interval = max(25, int(self.video_timer.interval() * 0.9))  # Decrease interval by 10%
                self.video_timer.setInterval(new_interval)
                print(f"📊 Performance: Improved frame interval to {new_interval}ms")

    def closeEvent(self, event):
        """Clean up when closing application"""
        self.detection_processor.stop()
        self.detection_processor.wait()
        
        # Clean up camera resources
        if self.esp32_camera:
            self.esp32_camera.release()
        if self.ip_camera:
            self.ip_camera.release()
        if self.local_camera:
            self.local_camera.release()
            
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
