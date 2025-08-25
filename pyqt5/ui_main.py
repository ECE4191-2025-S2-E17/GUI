# -*- coding: utf-8 -*-

# Robotic Platform Control Interface
# ECE4191 - Central Control and Monitoring Station
# This interface provides comprehensive control and monitoring capabilities
# for the robotic platform including drive controls, gimbal control,
# object detection display, and real-time telemetry.

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1400, 900)
        MainWindow.setMinimumSize(QtCore.QSize(1400, 900))
        
        # Main central widget
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            /* Header Styling */
            #Header {
                background-color: #1e1e1e;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                margin: 2px;
            }
            
            /* Video Feed Styling */
            #VideoContainer {
                background-color: #1e1e1e;
                border: 2px solid #2196F3;
                border-radius: 10px;
                margin: 5px;
            }
            
            #Video {
                background-color: #000000;
                border: 1px solid #555555;
                border-radius: 8px;
                margin: 10px;
            }
            
            /* Control Panel Styling */
            #ControlPanel {
                background-color: #1e1e1e;
                border: 2px solid #FF9800;
                border-radius: 10px;
                margin: 5px;
            }
            
            /* Detection Panel Styling */
            #DetectionPanel {
                background-color: #1e1e1e;
                border: 2px solid #9C27B0;
                border-radius: 10px;
                margin: 5px;
            }
            
            /* Status Panel Styling */
            #StatusPanel {
                background-color: #1e1e1e;
                border: 2px solid #F44336;
                border-radius: 10px;
                margin: 5px;
            }
            
            /* Button Styling */
            QPushButton {
                background-color: #3f3f3f;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 30px;
                font-size: 14px;
            }
            
            QPushButton:hover {
                background-color: #4f4f4f;
                border-color: #777777;
            }
            
            QPushButton:pressed {
                background-color: #2f2f2f;
                border-color: #ffffff;
            }
            
            QPushButton:disabled {
                background-color: #2a2a2a;
                border-color: #3a3a3a;
                color: #666666;
            }
            
            /* Highlighted button state for keyboard input */
            QPushButton.highlighted {
                background-color: #4CAF50 !important;
                border-color: #45a049 !important;
                color: #ffffff !important;
                font-weight: bold !important;
            }
            
            /* Emergency Stop Button */
            #emergencyStopBtn {
                background-color: #F44336;
                border-color: #D32F2F;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            
            #emergencyStopBtn:hover {
                background-color: #E53935;
            }
            
            /* Slider Styling */
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background: #3f3f3f;
                border-radius: 4px;
            }
            
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #45a049;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            
            /* Label Styling */
            QLabel {
                color: #ffffff;
            }
            
            /* List Widget Styling */
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444444;
            }
            
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            
            /* Progress Bar Styling */
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                background-color: #2a2a2a;
            }
            
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        self.centralwidget.setObjectName("centralwidget")
        
        # Main layout
        self.mainLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.mainLayout.setSpacing(10)
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        
        # Header Section
        self.Header = QtWidgets.QWidget()
        self.Header.setObjectName("Header")
        self.Header.setMaximumHeight(70)
        self.Header.setMinimumHeight(60)
        self.headerLayout = QtWidgets.QHBoxLayout(self.Header)
        
        # Title and Status
        self.titleLabel = QtWidgets.QLabel("Robotic Platform Control Interface")
        self.titleLabel.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50;")
        self.headerLayout.addWidget(self.titleLabel)
        
        self.headerLayout.addStretch()
        
        # Connection Status
        self.connectionStatus = QtWidgets.QLabel("Status: Disconnected")
        self.connectionStatus.setStyleSheet("font-size: 12px; color: #F44336;")
        self.headerLayout.addWidget(self.connectionStatus)
        
        # Emergency Stop Button
        self.emergencyStopBtn = QtWidgets.QPushButton("EMERGENCY STOP")
        self.emergencyStopBtn.setObjectName("emergencyStopBtn")
        self.emergencyStopBtn.setMinimumSize(120, 30)
        self.emergencyStopBtn.setMaximumSize(180, 40)
        self.headerLayout.addWidget(self.emergencyStopBtn)
        
        self.mainLayout.addWidget(self.Header)
        
        # Content Area
        self.contentLayout = QtWidgets.QHBoxLayout()
        
        # Left Column - Video and Detection
        self.leftColumn = QtWidgets.QVBoxLayout()
        
        # Video Container
        self.VideoContainer = QtWidgets.QWidget()
        self.VideoContainer.setObjectName("VideoContainer")
        self.videoLayout = QtWidgets.QVBoxLayout(self.VideoContainer)
        
        self.videoHeaderLabel = QtWidgets.QLabel("Live Camera Feed")
        self.videoHeaderLabel.setStyleSheet("font-size: 18px; color: #ffffff; margin: 5px;")  # Increased from 14px
        self.videoLayout.addWidget(self.videoHeaderLabel)
        
        self.Video = QtWidgets.QLabel()
        self.Video.setObjectName("Video")
        self.Video.setMinimumSize(QtCore.QSize(480, 360))
        self.Video.setAlignment(QtCore.Qt.AlignCenter)
        self.Video.setText("Camera Feed Loading...")
        self.Video.setStyleSheet("font-size: 18px; color: #888888; margin: 5px;")
        self.Video.setScaledContents(True)
        self.videoLayout.addWidget(self.Video, 1)
        
        self.leftColumn.addWidget(self.VideoContainer, 3)
        
        # Detection Panel
        self.DetectionPanel = QtWidgets.QWidget()
        self.DetectionPanel.setObjectName("DetectionPanel")
        self.detectionLayout = QtWidgets.QVBoxLayout(self.DetectionPanel)
        
        self.detectionHeaderLabel = QtWidgets.QLabel("Object/Audio Detection Results")
        self.detectionHeaderLabel.setStyleSheet("font-size: 18px; color: #ffffff; margin: 5px;")  # Increased from 14px
        self.detectionLayout.addWidget(self.detectionHeaderLabel)
        
        self.detectionList = QtWidgets.QListWidget()
        self.detectionList.setMinimumHeight(80)
        self.detectionLayout.addWidget(self.detectionList)
        
        self.leftColumn.addWidget(self.DetectionPanel, 1)
        
        self.contentLayout.addLayout(self.leftColumn, 3)
        
        # Right Column - Controls and Status
        self.rightColumn = QtWidgets.QVBoxLayout()
        
        # Control Panel
        self.ControlPanel = QtWidgets.QWidget()
        self.ControlPanel.setObjectName("ControlPanel")
        self.ControlPanel.setMinimumWidth(350)
        self.controlLayout = QtWidgets.QVBoxLayout(self.ControlPanel)
        
        self.controlHeaderLabel = QtWidgets.QLabel("Input Handler - Drive Controls")
        self.controlHeaderLabel.setStyleSheet("font-size: 20px; color: #ffffff; margin: 5px;")  # Increased from 16px
        self.controlLayout.addWidget(self.controlHeaderLabel)
        
        # Drive Controls
        self.driveControlsGroup = QtWidgets.QGroupBox("Vehicle Drive")
        self.driveControlsLayout = QtWidgets.QGridLayout(self.driveControlsGroup)
        self.driveControlsLayout.setSpacing(5)
        
        # Directional buttons - Scalable
        self.forwardBtn = QtWidgets.QPushButton("Forward (W)")
        self.forwardBtn.setMinimumSize(80, 40)
        self.forwardBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.forwardBtn.setObjectName("forwardBtn")
        self.driveControlsLayout.addWidget(self.forwardBtn, 0, 1)
        
        self.leftBtn = QtWidgets.QPushButton("Left (A)")
        self.leftBtn.setMinimumSize(80, 40)
        self.leftBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.leftBtn.setObjectName("leftBtn")
        self.driveControlsLayout.addWidget(self.leftBtn, 1, 0)
        
        self.stopBtn = QtWidgets.QPushButton("STOP")
        self.stopBtn.setMinimumSize(80, 40)
        self.stopBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.stopBtn.setObjectName("stopBtn")
        self.stopBtn.setStyleSheet("background-color: #F44336; border-color: #D32F2F; font-size: 14px; font-weight: bold;")
        self.driveControlsLayout.addWidget(self.stopBtn, 1, 1)
        
        self.rightBtn = QtWidgets.QPushButton("Right (D)")
        self.rightBtn.setMinimumSize(80, 40)
        self.rightBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.rightBtn.setObjectName("rightBtn")
        self.driveControlsLayout.addWidget(self.rightBtn, 1, 2)
        
        self.backwardBtn = QtWidgets.QPushButton("Backward (S)")
        self.backwardBtn.setMinimumSize(80, 40)
        self.backwardBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.backwardBtn.setObjectName("backwardBtn")
        self.driveControlsLayout.addWidget(self.backwardBtn, 2, 1)
        
        # Speed Control
        self.speedLabel = QtWidgets.QLabel("Drive Speed:")
        self.driveControlsLayout.addWidget(self.speedLabel, 3, 0)
        
        self.speedSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speedSlider.setRange(0, 100)
        self.speedSlider.setValue(50)
        self.driveControlsLayout.addWidget(self.speedSlider, 3, 1, 1, 2)
        
        self.speedValueLabel = QtWidgets.QLabel("50%")
        self.speedValueLabel.setMinimumWidth(40)
        self.driveControlsLayout.addWidget(self.speedValueLabel, 3, 3)
        
        self.controlLayout.addWidget(self.driveControlsGroup)
        
        # Gimbal Controls
        self.gimbalControlsGroup = QtWidgets.QGroupBox("Gimbal Control")
        self.gimbalControlsLayout = QtWidgets.QGridLayout(self.gimbalControlsGroup)
        self.gimbalControlsLayout.setSpacing(5)
        
        # Gimbal controls arranged in T-shape like drive controls
        # Tilt Up at top center
        self.tiltUpBtn = QtWidgets.QPushButton("Tilt Up (↑)")
        self.tiltUpBtn.setMinimumSize(80, 35)
        self.tiltUpBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.tiltUpBtn.setObjectName("tiltUpBtn")
        self.gimbalControlsLayout.addWidget(self.tiltUpBtn, 0, 1)
        
        # Pan Left, Center, Pan Right on middle row
        self.panLeftBtn = QtWidgets.QPushButton("Pan Left (←)")
        self.panLeftBtn.setMinimumSize(80, 35)
        self.panLeftBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.panLeftBtn.setObjectName("panLeftBtn")
        self.gimbalControlsLayout.addWidget(self.panLeftBtn, 1, 0)
        
        self.centerGimbalBtn = QtWidgets.QPushButton("Center Cam")
        self.centerGimbalBtn.setMinimumSize(80, 35)
        self.centerGimbalBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.centerGimbalBtn.setObjectName("centerGimbalBtn")
        self.gimbalControlsLayout.addWidget(self.centerGimbalBtn, 1, 1)
        
        self.panRightBtn = QtWidgets.QPushButton("Pan Right (→)")
        self.panRightBtn.setMinimumSize(80, 35)
        self.panRightBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.panRightBtn.setObjectName("panRightBtn")
        self.gimbalControlsLayout.addWidget(self.panRightBtn, 1, 2)
        
        # Tilt Down at bottom center
        self.tiltDownBtn = QtWidgets.QPushButton("Tilt Down (↓)")
        self.tiltDownBtn.setMinimumSize(80, 35)
        self.tiltDownBtn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.tiltDownBtn.setObjectName("tiltDownBtn")
        self.gimbalControlsLayout.addWidget(self.tiltDownBtn, 2, 1)
        
        self.controlLayout.addWidget(self.gimbalControlsGroup)
        
        self.rightColumn.addWidget(self.ControlPanel, 3)
        
        # Status Panel
        self.StatusPanel = QtWidgets.QWidget()
        self.StatusPanel.setObjectName("StatusPanel")
        self.StatusPanel.setMinimumWidth(300)
        self.statusLayout = QtWidgets.QVBoxLayout(self.StatusPanel)
        
        self.statusHeaderLabel = QtWidgets.QLabel("Data Display Renderer - Telemetry")
        self.statusHeaderLabel.setStyleSheet("font-size: 18px; color: #ffffff; margin: 5px;")  # Matched to other headers
        self.statusLayout.addWidget(self.statusHeaderLabel)
        
        # Create horizontal layout for telemetry sections
        self.telemetryHorizontalLayout = QtWidgets.QHBoxLayout()
        
        # System Status - Left side (takes up left column)
        self.systemStatusGroup = QtWidgets.QGroupBox("System Status")
        self.systemStatusLayout = QtWidgets.QVBoxLayout(self.systemStatusGroup)
        
        # Connection indicators
        self.robotConnectionLabel = QtWidgets.QLabel("Robot Connection: Offline")
        self.robotConnectionLabel.setStyleSheet("color: #F44336;")
        self.robotConnectionLabel.setWordWrap(True)
        self.systemStatusLayout.addWidget(self.robotConnectionLabel)
        
        self.cameraConnectionLabel = QtWidgets.QLabel("Camera Feed: Offline")
        self.cameraConnectionLabel.setStyleSheet("color: #F44336;")
        self.cameraConnectionLabel.setWordWrap(True)
        self.systemStatusLayout.addWidget(self.cameraConnectionLabel)
        
        # Battery status
        self.batteryLabel = QtWidgets.QLabel("Battery Level:")
        self.systemStatusLayout.addWidget(self.batteryLabel)
        
        self.batteryProgress = QtWidgets.QProgressBar()
        self.batteryProgress.setValue(75)
        self.batteryProgress.setMinimumHeight(20)
        self.systemStatusLayout.addWidget(self.batteryProgress)
        
        # Add system status to left side of horizontal layout
        self.telemetryHorizontalLayout.addWidget(self.systemStatusGroup, 1)
        
        # Right side - Vertical layout for Motor and Communication
        self.rightSideLayout = QtWidgets.QVBoxLayout()
        
        # Motor Encoder Feedback - Top right
        self.motorStatusGroup = QtWidgets.QGroupBox("Motor Encoder Feedback")
        self.motorStatusLayout = QtWidgets.QVBoxLayout(self.motorStatusGroup)
        
        self.leftMotorLabel = QtWidgets.QLabel("Left Motor: 0 RPM")
        self.leftMotorLabel.setWordWrap(True)
        self.motorStatusLayout.addWidget(self.leftMotorLabel)
        
        self.rightMotorLabel = QtWidgets.QLabel("Right Motor: 0 RPM")
        self.rightMotorLabel.setWordWrap(True)
        self.motorStatusLayout.addWidget(self.rightMotorLabel)
        
        self.suspensionHeightLabel = QtWidgets.QLabel("Suspension Height: 15.2 cm")
        self.suspensionHeightLabel.setWordWrap(True)
        self.motorStatusLayout.addWidget(self.suspensionHeightLabel)
        
        self.rightSideLayout.addWidget(self.motorStatusGroup)
        
        # Communication Interface - Bottom right
        self.commGroup = QtWidgets.QGroupBox("Communication Interface")
        self.commLayout = QtWidgets.QVBoxLayout(self.commGroup)
        
        self.packetsSentLabel = QtWidgets.QLabel("Packets Sent: 0")
        self.packetsSentLabel.setWordWrap(True)
        self.commLayout.addWidget(self.packetsSentLabel)
        
        self.packetsReceivedLabel = QtWidgets.QLabel("Packets Received: 0")
        self.packetsReceivedLabel.setWordWrap(True)
        self.commLayout.addWidget(self.packetsReceivedLabel)
        
        self.latencyLabel = QtWidgets.QLabel("Latency: -- ms")
        self.latencyLabel.setWordWrap(True)
        self.commLayout.addWidget(self.latencyLabel)
        
        self.rightSideLayout.addWidget(self.commGroup)
        
        # Add right side layout to horizontal layout
        self.telemetryHorizontalLayout.addLayout(self.rightSideLayout, 1)
        
        # Add horizontal layout to main status layout
        self.statusLayout.addLayout(self.telemetryHorizontalLayout)
        
        self.rightColumn.addWidget(self.StatusPanel, 2)
        
        self.contentLayout.addLayout(self.rightColumn, 2)
        self.mainLayout.addLayout(self.contentLayout)
        
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "ECE4191 - Robotic Platform Control Interface"))
