// Direct WebSocket connection to ESP32 Motor Controller
ESP_IP = window.env.ESP_IP;
if (!ESP_IP) {
  console.error("ESP_IP is not defined in environment variables.");
  updateRobotStatus("❌", "No ESP_IP");
}
const WS_URL = `ws://${ESP_IP}:85`;

let socket = null;
let linearSpeed = 50; // Forward/backward speed
let angularSpeed = 50; // Turning speed
const SPEED_INCREMENT = 10;
const MAX_SPEED = 100;
const MIN_SPEED = -100;

// Track which movement keys are pressed
let keysPressed = {
  w: false,
  s: false,
  a: false,
  d: false,
};

// Robot state data from STM32
let robotState = {
  wheelSpeeds: { FL: 0, FR: 0 }, // RPM (mocked - no longer receiving from websocket)
  suspension: { height: 0, pulses: 0 },
};
let prev_suspension = 100000;

// Mock wheel speed state
let mockWheelSpeeds = { FL: 0, FR: 0 };
let targetWheelSpeeds = { FL: 0, FR: 0 };
const RAMP_RATE = 2; // RPM per frame (acceleration)
const DECEL_RATE = 1.1; // RPM per frame (deceleration) - slower for realistic coast
const MAX_RPM = 15;
const RANDOMNESS = 0.95; // 0.95 = ±5% random variation
const ENCODER_ERROR_CHANCE = 0.15; // 15% chance per frame to drop to noise level

// Update mock wheel speeds with ramping animation
function updateMockWheelSpeeds() {
  // Ramp towards target speeds
  Object.keys(mockWheelSpeeds).forEach((wheel) => {
    const current = mockWheelSpeeds[wheel];
    const target = targetWheelSpeeds[wheel];
    const diff = target - current;

    if (Math.abs(diff) > (target > current ? RAMP_RATE : DECEL_RATE)) {
      mockWheelSpeeds[wheel] += Math.sign(diff) * (target > current ? RAMP_RATE : DECEL_RATE);
    } else {
      mockWheelSpeeds[wheel] = target;
    }

    // When coasting to a stop (target is 0), occasionally drop to encoder noise level
    if (target === 0 && Math.abs(mockWheelSpeeds[wheel]) > 0.2) {
      if (Math.random() < ENCODER_ERROR_CHANCE) {
        mockWheelSpeeds[wheel] = (Math.random() - 0.5) * 0.2; // Small noise 0~0.2
      }
    } else if (target === 0 && Math.abs(mockWheelSpeeds[wheel]) <= 0.2) {
      // Once very slow, mostly stay at 0, occasional noise
      if (Math.random() < 0.3) {
        mockWheelSpeeds[wheel] = (Math.random() - 0.5) * 0.1;
      } else {
        mockWheelSpeeds[wheel] = 0;
      }
    }

    // Add slight random variation during active movement
    if (Math.abs(target) > 1) {
      mockWheelSpeeds[wheel] *= RANDOMNESS + Math.random() * (1 - RANDOMNESS);
    }
  });

  robotState.wheelSpeeds = { ...mockWheelSpeeds };
  updateRoverDisplay();
}

// Calculate target wheel speeds based on linear speed
function calculateTargetRPM(linear, angular) {
  const baseRPM = (Math.abs(linear) / 100) * MAX_RPM;
  const angularRPM = (Math.abs(angular) / 100) * MAX_RPM;
  
  return {
    FL: baseRPM + angularRPM,
    FR: baseRPM + angularRPM,
  };
}

// Start mock wheel speed animation loop
let mockSpeedInterval = setInterval(updateMockWheelSpeeds, 50);
// Initialize WebSocket connection
function initWebSocket() {
  console.log("=== WebSocket Initialization ===");
  console.log("ESP_IP:", ESP_IP);
  console.log("WS_URL:", WS_URL);
  console.log("Attempting to connect...");

  try {
    socket = new WebSocket(WS_URL);
    console.log("WebSocket object created, state:", socket.readyState);
    // readyState: 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED

    socket.onopen = function () {
      console.log("✓ WebSocket OPENED - Connected to ESP32 Motor Controller");
      console.log("  readyState:", socket.readyState);
      updateRobotStatus("🟢", "Connected");
    };

    socket.onclose = function (event) {
      console.log("✗ WebSocket CLOSED");
      console.log("  Code:", event.code);
      console.log("  Reason:", event.reason || "No reason provided");
      console.log("  Was clean:", event.wasClean);
      updateRobotStatus("❌", "Disconnected");
      console.log("  Reconnecting in 1 second...");
      setTimeout(initWebSocket, 1000);
    };

    socket.onerror = function (error) {
      console.error("✗ WebSocket ERROR occurred:");
      console.error("  Error object:", error);
      console.error("  readyState:", socket.readyState);
      updateRobotStatus("❌", "Error");
    };

    socket.onmessage = function (event) {
      const message = event.data;

      // Handle different message types
      if (message.startsWith("DATA:")) {
        handleDataMessage(message);
      } else if (message.startsWith("DEBUG:") || message.startsWith("INFO:")) {
        console.log(message);
      } else if (message.startsWith("WARNING:")) {
        console.warn(message);
      } else if (message.startsWith("ERROR:")) {
        console.error(message);
      } else {
        console.log("Received:", message);
      }
    };
  } catch (e) {
    console.error("✗ EXCEPTION creating WebSocket:");
    console.error("  Exception:", e);
    console.error("  Message:", e.message);
    updateRobotStatus("❌", "Init Error");
  }
}

// Helper to send control request to ESP32 camera control endpoint
function cameraControl(varName, val) {
  // Update visible value next to slider
  const span = document.getElementById(`${varName}-val`);
  if (span) span.textContent = val;

  if (!window.env || !window.env.ESP_IP) {
    console.error("ESP_IP not available for cameraControl");
    return;
  }

  const url = `http://${window.env.ESP_IP}/control?var=${encodeURIComponent(
    varName
  )}&val=${encodeURIComponent(val)}`;
  // Use fetch so it's asynchronous and doesn't block UI
  fetch(url)
    .then((resp) => {
      if (!resp.ok) {
        console.error("Camera control failed", resp.status);
      }
    })
    .catch((err) => console.error("Camera control error", err));
}

// Parse DATA messages from STM32
function handleDataMessage(message) {
  // Remove "DATA: " prefix
  console.log("Received DATA message:", message);
  //2147483281 ->
  const data = message.substring(6);

  // Parse wheel speeds: "Wheel Speeds (RPM) - FL:%+.1f RL:%+.1f FR:%+.1f RR:%+.1f"
  const wheelSpeedMatch = data.match(
    /Wheel Speeds \(RPM\) - FL:([+-]?\d+\.?\d*) RL:([+-]?\d+\.?\d*) FR:([+-]?\d+\.?\d*) RR:([+-]?\d+\.?\d*)/
  );
  if (wheelSpeedMatch) {
    robotState.wheelSpeeds = {
      FL: parseFloat(wheelSpeedMatch[1]),
      RL: parseFloat(wheelSpeedMatch[2]),
      FR: parseFloat(wheelSpeedMatch[3]),
      RR: parseFloat(wheelSpeedMatch[4]),
    };
    console.log("Wheel Speeds:", robotState.wheelSpeeds);
    updateRoverDisplay(); // Update display immediately when new data arrives
    return;
  }

  // Parse suspension: "Suspension <number>"
  const suspensionMatch = data.match(
    /Suspension ([+-]?\d+)/
  );
  if (suspensionMatch) {
    const pulses = parseInt(suspensionMatch[1]);
    const pulseChange = pulses - prev_suspension;
    prev_suspension = pulses;
    robotState.suspension = {
      height: robotState.suspension.height - pulseChange * (1/20),
      pulses: pulses,
    };
    console.log("Suspension:", robotState.suspension);
    console.log("Height:", robotState.suspension.height);
    console.log("Pulses:", robotState.suspension.pulses);
    updateHeightDisplay(); // Update display immediately when new data arrives
    return;
  }

  // Log unrecognized DATA messages
  console.log("Unknown DATA format:", data);
}

// Send command to ESP32
function sendCommand(command) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(command);
    console.log("Sent command:", command);
    return true;
  } else {
    console.error("WebSocket not connected");
    return false;
  }
}

// Convert linear and angular speed to differential wheel speeds
function calculateWheelSpeeds(linear, angular) {
  // Differential drive:
  // left wheel = linear - angular
  // right wheel = linear + angular
  let leftWheel = linear - angular;
  let rightWheel = linear + angular;

  // Clamp to valid range
  leftWheel = Math.max(MIN_SPEED, Math.min(MAX_SPEED, leftWheel));
  rightWheel = Math.max(MIN_SPEED, Math.min(MAX_SPEED, rightWheel));

  return { left: Math.round(leftWheel), right: Math.round(rightWheel) };
}

// Send wheel speed command using current linear and angular speeds
function sendWheelCommand() {
  const speeds = calculateWheelSpeeds(linearSpeed, angularSpeed);
  const command = `LW:${speeds.left},RW:${speeds.right}`;
  sendCommand(command);
  return speeds;
}

// Update movement based on currently pressed keys
function updateMovement() {
  let appliedLinear = 0;
  let appliedAngular = 0;

  // Apply linear speed when W or S is pressed
  if (keysPressed.w && !keysPressed.s) {
    appliedLinear = linearSpeed; // Use current linear speed setting
  } else if (keysPressed.s && !keysPressed.w) {
    appliedLinear = -linearSpeed; // Reverse direction
  }

  // Apply angular speed when A or D is pressed
  if (keysPressed.a && !keysPressed.d) {
    appliedAngular = angularSpeed; // Turn left (negative angular)
  } else if (keysPressed.d && !keysPressed.a) {
    appliedAngular = -angularSpeed; // Turn right (positive angular)
  }

  // Calculate and send wheel speeds
  const speeds = calculateWheelSpeeds(appliedLinear, appliedAngular);
  const command = `LW:${speeds.left},RW:${speeds.right}`;
  sendCommand(command);

  // Update target mock wheel speeds
  const targetRPM = calculateTargetRPM(appliedLinear, appliedAngular);
  targetWheelSpeeds.FL = targetRPM.FL;
  targetWheelSpeeds.FR = targetRPM.FR;
}

function highlightKey(id, active) {
  const key = document.getElementById(id);
  if (key) {
    key.classList.toggle("active", active);
  }
}

document.addEventListener("keydown", function (event) {
  // Prevent default for arrow keys and prevent key repeat
  if (event.key.startsWith("Arrow")) {
    event.preventDefault();
  }
  if (event.repeat) return; // Ignore key repeat

  switch (event.key) {
    // Drive - WASD controls movement (linear and angular)
    case "w":
      highlightKey("key-w", true);
      keysPressed.w = true;
      updateMovement();
      break;
    case "s":
      highlightKey("key-s", true);
      keysPressed.s = true;
      updateMovement();
      break;
    case "a":
      highlightKey("key-a", true);
      keysPressed.a = true;
      updateMovement();
      break;
    case "d":
      highlightKey("key-d", true);
      keysPressed.d = true;
      updateMovement();
      break;

    // Arrow keys set base speed values
    case "ArrowUp":
      // highlightKey("key-up", true);
      // Increase base linear speed
      linearSpeed = Math.min(MAX_SPEED, linearSpeed + SPEED_INCREMENT);
      updateMovement(); // Reapply with new base speed
      break;
    case "ArrowDown":
      // highlightKey("key-down", true);
      // Decrease base linear speed
      linearSpeed = Math.max(0, linearSpeed - SPEED_INCREMENT);
      updateMovement(); // Reapply with new base speed
      break;
    case "ArrowLeft":
      // highlightKey("key-left", true);
      // Decrease base angular speed
      angularSpeed = Math.max(0, angularSpeed - SPEED_INCREMENT);
      updateMovement(); // Reapply with new base speed
      break;
    case "ArrowRight":
      // highlightKey("key-right", true);
      // Increase base angular speed
      angularSpeed = Math.min(MAX_SPEED, angularSpeed + SPEED_INCREMENT);
      updateMovement(); // Reapply with new base speed
      break;

    // Suspension controls
    case "q":
    case "Q":
      highlightKey("key-q", true);
      sendCommand("SUS:UP");
      break;
    case "e":
    case "E":
      highlightKey("key-e", true);
      sendCommand("SUS:DOWN");
      break;

    // Gimbal Pan - J/L keys
    case "j":
    case "J":
      highlightKey("key-j", true);
      sendCommand("PAN:LEFT");
      break;
    case "l":
    case "L":
      highlightKey("key-l", true);
      sendCommand("PAN:RIGHT");
      break;

    // Gimbal Tilt - I/K keys
    case "i":
    case "I":
      highlightKey("key-i", true);
      sendCommand("TILT:UP");
      break;
    case "k":
    case "K":
      highlightKey("key-k", true);
      sendCommand("TILT:DOWN");
      break;

    // Emergency stop
    case " ":
      highlightKey("key-space", true);
      sendCommand("STOPALL");
      break;
  }
});

document.addEventListener("keyup", function (event) {
  switch (event.key) {
    // Drive keys - update movement state
    case "w":
      highlightKey("key-w", false);
      keysPressed.w = false;
      updateMovement();
      break;
    case "s":
      highlightKey("key-s", false);
      keysPressed.s = false;
      updateMovement();
      break;
    case "a":
      highlightKey("key-a", false);
      keysPressed.a = false;
      updateMovement();
      break;
    case "d":
      highlightKey("key-d", false);
      keysPressed.d = false;
      updateMovement();
      break;

    // Arrow keys - no action on release (speed is maintained)
    case "ArrowLeft":
      // highlightKey("key-left", false);
      break;
    case "ArrowRight":
      // highlightKey("key-right", false);
      break;
    case "ArrowUp":
      // highlightKey("key-up", false);
      break;
    case "ArrowDown":
      // highlightKey("key-down", false);
      break;

    // Suspension keys - stop on release
    case "q":
    case "Q":
      highlightKey("key-q", false);
      sendCommand("SUS:STOP");
      break;
    case "e":
    case "E":
      highlightKey("key-e", false);
      sendCommand("SUS:STOP");
      break;

    // Gimbal Pan - stop on release
    case "j":
    case "J":
      highlightKey("key-j", false);
      sendCommand("PAN:STOP");
      break;
    case "l":
    case "L":
      highlightKey("key-l", false);
      sendCommand("PAN:STOP");
      break;

    // Gimbal Tilt - stop on release
    case "i":
    case "I":
      highlightKey("key-i", false);
      sendCommand("TILT:STOP");
      break;
    case "k":
    case "K":
      highlightKey("key-k", false);
      sendCommand("TILT:STOP");
      break;

    // Spacebar
    case " ":
      highlightKey("key-space", false);
      break;
  }
});

// Height display functions - uses robotState.suspension
function updateHeightDisplay() {
  const heightNumber = document.getElementById("height-number");
  const heightFill = document.getElementById("height-fill");
  const heightIndicator = document.getElementById("height-indicator");

  if (heightNumber && heightFill && heightIndicator) {
    const height = robotState.suspension.height || 72; // Use real data or default to 72mm
    const minHeight = 70; // Minimum height 70mm
    const maxHeight = 150; // Maximum height 150mm

    // Update number display
    heightNumber.textContent = height.toFixed(1);

    // Calculate percentage for bar fill
    const percentage = ((height - minHeight) / (maxHeight - minHeight)) * 100;
    heightFill.style.height = `${Math.max(0, Math.min(100, percentage))}%`;

    // Update indicator position
    const indicatorTop = 100 - percentage;
    heightIndicator.style.top = `${Math.max(0, Math.min(100, indicatorTop))}%`;
  }
}

// Zero suspension function
function zeroSuspension() {
  robotState.suspension.height = 140;
  console.log("Sent zero suspension command");
  updateHeightDisplay();
}

// Rover speed display functions - uses robotState.wheelSpeeds
function updateRoverDisplay() {
  // Use actual wheel speeds (now mocked)
  const leftSpeed = robotState.wheelSpeeds.FL;
  const rightSpeed = robotState.wheelSpeeds.FR;

  // Update speed displays
  document.querySelectorAll(".left-wheels .speed-text").forEach((el) => {
    el.textContent = `${Math.abs(leftSpeed).toFixed(1)} cm/s`;
  });
  document.querySelectorAll(".right-wheels .speed-text").forEach((el) => {
    el.textContent = `${Math.abs(rightSpeed).toFixed(1)} cm/s`;
  });

  // Update wheel indicators
  document.querySelectorAll(".left-wheels .wheel").forEach((wheel) => {
    wheel.classList.toggle("active", leftSpeed !== 0);
  });
  document.querySelectorAll(".right-wheels .wheel").forEach((wheel) => {
    wheel.classList.toggle("active", rightSpeed !== 0);
  });
}

// Update rover display with current speeds
function updateRoverSpeedDisplay() {
  // Calculate actual applied speeds based on pressed keys
  let appliedLinear = 0;
  let appliedAngular = 0;

  if (keysPressed.w && !keysPressed.s) {
    appliedLinear = linearSpeed;
  } else if (keysPressed.s && !keysPressed.w) {
    appliedLinear = -linearSpeed;
  }

  if (keysPressed.a && !keysPressed.d) {
    appliedAngular = -angularSpeed;
  } else if (keysPressed.d && !keysPressed.a) {
    appliedAngular = angularSpeed;
  }

  // Update linear and angular speed displays
  const linearSpeedDisplay = document.getElementById("linear-speed-display");
  const angularSpeedDisplay = document.getElementById("angular-speed-display");

  if (linearSpeedDisplay) {
    linearSpeedDisplay.textContent = linearSpeed;
  }

  if (angularSpeedDisplay) {
    angularSpeedDisplay.textContent = angularSpeed;
  }

  // Update debug info if element exists
  const debugInfo = document.getElementById("speed-debug");
  if (debugInfo) {
    debugInfo.textContent = `Base L:${linearSpeed} A:${angularSpeed} | Applied L:${appliedLinear} A:${appliedAngular} | Wheels L:${speeds.left} R:${speeds.right}`;
  }
}

// Initialize WebSocket and displays when page loads
document.addEventListener("DOMContentLoaded", function () {
  initWebSocket();
  updateHeightDisplay();
  updateRoverDisplay();

  // Initialize camera tuning sliders from env if provided
  if (window.env && window.env.camera_config) {
    const cfg = window.env.camera_config;
    Object.keys(cfg).forEach((k) => {
      const el = document.getElementById(k);
      const span = document.getElementById(`${k}-val`);
      if (el) {
        try {
          el.value = cfg[k];
        } catch (e) {
          console.warn("Failed to set slider", k, e);
        }
      }
      if (span) span.textContent = cfg[k];
    });
  }

  // Update command speed display periodically (user input feedback)
  setInterval(() => {
    updateRoverSpeedDisplay(); // Shows current command speeds
  }, 100);
});

// Update robot status indicator in the status partial
function updateRobotStatus(icon, status) {
  const robotStatusIcon = document.getElementById("robot-status-icon");
  if (robotStatusIcon) {
    robotStatusIcon.textContent = icon;
    robotStatusIcon.title = status; // Add tooltip with status text
  }
}
