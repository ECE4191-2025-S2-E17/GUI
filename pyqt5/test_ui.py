#!/usr/bin/env python3
"""
Simple test script to display the UI without functionality
Run this to see just the GUI layout and design
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt
from ui_main import Ui_MainWindow


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Setup UI from Designer
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Set window title
        self.setWindowTitle("ECE4191 - UI Design Preview")
        
        # Enable keyboard input for testing
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Track pressed keys
        self.pressed_keys = set()
        
        # Populate with some test data to show how it looks
        self.populate_test_data()
        
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
        
    def keyPressEvent(self, event):
        """Display keyboard input feedback for testing"""
        key = event.key()
        
        # Avoid repeat events
        if key in self.pressed_keys:
            return
            
        self.pressed_keys.add(key)
        
        # Show which keys are being pressed and highlight buttons
        key_info = {
            Qt.Key_W: ("W (Forward)", self.ui.forwardBtn),
            Qt.Key_A: ("A (Left)", self.ui.leftBtn), 
            Qt.Key_S: ("S (Backward)", self.ui.backwardBtn),
            Qt.Key_D: ("D (Right)", self.ui.rightBtn),
            Qt.Key_Left: ("← (Pan Left)", self.ui.panLeftBtn),
            Qt.Key_Right: ("→ (Pan Right)", self.ui.panRightBtn),
            Qt.Key_Up: ("↑ (Tilt Up)", self.ui.tiltUpBtn),
            Qt.Key_Down: ("↓ (Tilt Down)", self.ui.tiltDownBtn),
            Qt.Key_Space: ("SPACE (Emergency Stop)", self.ui.emergencyStopBtn)
        }
        
        if key in key_info:
            key_name, button = key_info[key]
            self.highlight_button(button, True)
            self.ui.Video.setText(f"Key Pressed: {key_name}\n\n✅ Button Highlighted!\n\nKeyboard Controls:\nWASD - Drive Control\nArrow Keys - Gimbal Control\nSPACE - Emergency Stop\n\nRelease key to remove highlight")
        
        super().keyPressEvent(event)
        
    def keyReleaseEvent(self, event):
        """Handle key release and remove highlights"""
        key = event.key()
        
        self.pressed_keys.discard(key)
        
        # Remove highlights
        key_buttons = {
            Qt.Key_W: self.ui.forwardBtn,
            Qt.Key_A: self.ui.leftBtn,
            Qt.Key_S: self.ui.backwardBtn,
            Qt.Key_D: self.ui.rightBtn,
            Qt.Key_Left: self.ui.panLeftBtn,
            Qt.Key_Right: self.ui.panRightBtn,
            Qt.Key_Up: self.ui.tiltUpBtn,
            Qt.Key_Down: self.ui.tiltDownBtn,
            Qt.Key_Space: self.ui.emergencyStopBtn
        }
        
        if key in key_buttons:
            self.highlight_button(key_buttons[key], False)
            self.ui.Video.setText("Key Released - Highlight Removed\n\nKeyboard Controls:\nWASD - Drive Control\nArrow Keys - Gimbal Control\nSPACE - Emergency Stop\n\nTry pressing keys to test!")
        
        super().keyReleaseEvent(event)
        
    def populate_test_data(self):
        """Add some sample data to show how the interface looks"""
        # Add some sample detections
        sample_detections = [
            "[12:34:56] Kangaroo (Confidence: 89%)",
            "[12:35:12] Bird (Confidence: 76%)", 
            "[12:35:45] Vehicle (Confidence: 92%)",
            "[12:36:01] Person (Confidence: 84%)",
            "[12:36:23] Audio Alert (Confidence: 78%)"
        ]
        
        for detection in sample_detections:
            self.ui.detectionList.addItem(detection)
        
        # Set some sample values
        self.ui.speedSlider.setValue(65)
        self.ui.speedValueLabel.setText("65%")
        self.ui.batteryProgress.setValue(73)
        
        # Update connection status to show connected state
        self.ui.connectionStatus.setText("Status: Connected")
        self.ui.connectionStatus.setStyleSheet("color: #4CAF50;")
        self.ui.robotConnectionLabel.setText("Robot Connection: Online")
        self.ui.robotConnectionLabel.setStyleSheet("color: #4CAF50;")
        self.ui.cameraConnectionLabel.setText("Camera Feed: Online")
        self.ui.cameraConnectionLabel.setStyleSheet("color: #4CAF50;")
        
        # Update telemetry values
        self.ui.leftMotorLabel.setText("Left Motor: 145 RPM")
        self.ui.rightMotorLabel.setText("Right Motor: 142 RPM")
        self.ui.suspensionHeightLabel.setText("Suspension Height: 16.8 cm")
        self.ui.packetsSentLabel.setText("Packets Sent: 1,247")
        self.ui.packetsReceivedLabel.setText("Packets Received: 1,239")
        self.ui.latencyLabel.setText("Latency: 32 ms")
        
        # Set placeholder text for video
        self.ui.Video.setText("Camera Feed Preview\n\n(Video feed would appear here when running main.py)\n\nKeyboard Controls:\nWASD - Drive Control\nArrow Keys - Gimbal Control\nSPACE - Emergency Stop\n\nTry pressing keys to test!")
        self.ui.Video.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px dashed #555555;
                border-radius: 8px;
                color: #888888;
                font-size: 14px;
                text-align: center;
                padding: 20px;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create and show the test window
    window = TestWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    
    # Center the window on screen
    screen = app.primaryScreen()
    screen_geometry = screen.availableGeometry()
    window_geometry = window.frameGeometry()
    center_point = screen_geometry.center()
    window_geometry.moveCenter(center_point)
    window.move(window_geometry.topLeft())
    
    sys.exit(app.exec_())
