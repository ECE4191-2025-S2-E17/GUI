import websocket
import threading
import time
from flask_socketio import SocketIO, emit
from abc import ABC, abstractmethod
from enum import Enum


class DriveDirection(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    STOP = "stop"


class WebSocketDriveController:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.connected = False
        self.ws = None
        self.reconnect_thread = None
        self.should_reconnect = True
        self.left_wheel_speed = 0
        self.right_wheel_speed = 0

    def connect(self):
        """Establish WebSocket connection"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )

            # Start connection in separate thread
            def run_ws():
                self.ws.run_forever()

            ws_thread = threading.Thread(target=run_ws, daemon=True)
            ws_thread.start()

        except Exception as e:
            print(f"WebSocket connection error: {e}")
            self.connected = False

    def disconnect(self):
        """Close WebSocket connection"""
        self.should_reconnect = False
        if self.ws:
            self.ws.close()
        self.connected = False

    def _on_open(self, ws):
        """WebSocket connection opened"""
        self.connected = True
        print("WebSocket connected to drive controller")

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        # Leave empty as requested
        pass

    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
        self.connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        self.connected = False
        print("WebSocket connection closed")

        # Auto-reconnect if needed
        if self.should_reconnect:
            time.sleep(2)
            self.connect()

    def send_command(self, command: str):
        """Send command via WebSocket"""
        if self.connected and self.ws:
            try:
                # Ensure command ends with newline
                if not command.endswith("\n"):
                    command += "\n"
                self.ws.send(command)
                return True
            except Exception as e:
                print(f"Error sending command: {e}")
                self.connected = False
                return False
        return False

    def is_connected(self) -> bool:
        return self.connected

    def driveGimbalPan(self, direction: DriveDirection):
        """Control gimbal pan movement"""
        if direction == DriveDirection.FORWARD:
            return self.send_command("PAN:LEFT")
        elif direction == DriveDirection.BACKWARD:
            return self.send_command("PAN:RIGHT")
        else:
            return self.send_command("PAN:STOP")

    def driveGimbalTilt(self, direction: DriveDirection):
        """Control gimbal tilt movement"""
        if direction == DriveDirection.FORWARD:
            return self.send_command("TILT:UP")
        elif direction == DriveDirection.BACKWARD:
            return self.send_command("TILT:DOWN")
        else:
            return self.send_command("TILT:STOP")

    def driveSuspension(self, direction: DriveDirection):
        """Control suspension movement"""
        if direction == DriveDirection.FORWARD:
            return self.send_command("SUS:UP")
        elif direction == DriveDirection.BACKWARD:
            return self.send_command("SUS:DOWN")
        else:
            return self.send_command("SUS:STOP")

    def driveWheels(self, left_speed: int, right_speed: int):
        """Drive wheels with specific speeds (-100 to 100)"""
        # Clamp speeds to valid range
        left_speed = max(-100, min(100, left_speed))
        right_speed = max(-100, min(100, right_speed))

        self.left_wheel_speed = left_speed
        self.right_wheel_speed = right_speed

        command = f"LW:{left_speed},RW:{right_speed}"
        return self.send_command(command)

    def changeLeftWheelSpeed(self, delta: int):
        """Change left wheel speed by delta amount"""
        new_speed = max(-100, min(100, self.left_wheel_speed + delta))
        return self.driveWheels(new_speed, self.right_wheel_speed)

    def changeRightWheelSpeed(self, delta: int):
        """Change right wheel speed by delta amount"""
        new_speed = max(-100, min(100, self.right_wheel_speed + delta))
        return self.driveWheels(self.left_wheel_speed, new_speed)

    def driveWheelsVelocity(self, linear: float, angular: float):
        """Drive using linear and angular velocity (differential drive)"""
        # Convert linear/angular to left/right wheel speeds
        # Simple differential drive calculation
        wheel_base = 1.0  # Adjust based on robot specifications
        left_speed = int((linear - angular * wheel_base / 2) * 100)
        right_speed = int((linear + angular * wheel_base / 2) * 100)

        return self.driveWheels(left_speed, right_speed)

    def stop_all(self):
        """Stop all movement"""
        return self.send_command("STOPALL")
