// Direct WebSocket connection to ESP32 Motor Controller
testing = true;
const WS_URL = testing ? "wss://echo.websocket.org" : "ws://192.168.107.98:85";

let socket = null;
let linearSpeed = 0; // Forward/backward speed
let angularSpeed = 0; // Turning speed
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
  wheelSpeeds: { FL: 0, RL: 0, FR: 0, RR: 0 }, // RPM
  suspension: { height: 0, pulses: 0 },
};

// Initialize WebSocket connection
function initWebSocket() {
  socket = new WebSocket(WS_URL);

  socket.onopen = function () {
    console.log("Connected to ESP32 Motor Controller");
  };

  socket.onclose = function () {
    console.log("Disconnected from ESP32. Reconnecting...");
    setTimeout(initWebSocket, 1000); // Reconnect after 2 seconds
  };

  socket.onerror = function (error) {
    console.error("WebSocket error:", error);
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
}

// Parse DATA messages from STM32
function handleDataMessage(message) {
  // Remove "DATA: " prefix
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

  // Parse suspension: "Suspension %.2f (Total Pulses: %+ld)"
  const suspensionMatch = data.match(
    /Suspension ([+-]?\d+\.?\d*) \(Total Pulses: ([+-]?\d+)\)/
  );
  if (suspensionMatch) {
    robotState.suspension = {
      height: parseFloat(suspensionMatch[1]),
      pulses: parseInt(suspensionMatch[2]),
    };
    console.log("Suspension:", robotState.suspension);
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
    appliedAngular = -angularSpeed; // Turn left (negative angular)
  } else if (keysPressed.d && !keysPressed.a) {
    appliedAngular = angularSpeed; // Turn right (positive angular)
  }

  // Calculate and send wheel speeds
  const speeds = calculateWheelSpeeds(appliedLinear, appliedAngular);
  const command = `LW:${speeds.left},RW:${speeds.right}`;
  sendCommand(command);
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
      highlightKey("key-up", true);
      // Increase base linear speed
      linearSpeed = Math.min(MAX_SPEED, linearSpeed + SPEED_INCREMENT);
      updateMovement(); // Reapply with new base speed
      break;
    case "ArrowDown":
      highlightKey("key-down", true);
      // Decrease base linear speed
      linearSpeed = Math.max(0, linearSpeed - SPEED_INCREMENT);
      updateMovement(); // Reapply with new base speed
      break;
    case "ArrowLeft":
      highlightKey("key-left", true);
      // Decrease base angular speed
      angularSpeed = Math.max(0, angularSpeed - SPEED_INCREMENT);
      updateMovement(); // Reapply with new base speed
      break;
    case "ArrowRight":
      highlightKey("key-right", true);
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
      sendCommand("PAN:LEFT");
      break;
    case "l":
    case "L":
      sendCommand("PAN:RIGHT");
      break;

    // Gimbal Tilt - I/K keys
    case "i":
    case "I":
      sendCommand("TILT:UP");
      break;
    case "k":
    case "K":
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
      highlightKey("key-left", false);
      break;
    case "ArrowRight":
      highlightKey("key-right", false);
      break;
    case "ArrowUp":
      highlightKey("key-up", false);
      break;
    case "ArrowDown":
      highlightKey("key-down", false);
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
      sendCommand("PAN:STOP");
      break;
    case "l":
    case "L":
      sendCommand("PAN:STOP");
      break;

    // Gimbal Tilt - stop on release
    case "i":
    case "I":
      sendCommand("TILT:STOP");
      break;
    case "k":
    case "K":
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
    const maxHeight = 120; // Maximum height 120mm

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

// Rover speed display functions - uses robotState.wheelSpeeds
function updateRoverDisplay() {
  // Use actual wheel speeds from STM32
  const leftSpeed = (robotState.wheelSpeeds.FL + robotState.wheelSpeeds.RL) / 2;
  const rightSpeed =
    (robotState.wheelSpeeds.FR + robotState.wheelSpeeds.RR) / 2;

  // Update speed displays (convert RPM to approximate cm/s if needed, or just show RPM)
  document.querySelectorAll(".left-wheels .speed-text").forEach((el) => {
    el.textContent = `${Math.abs(leftSpeed).toFixed(1)} RPM`;
  });
  document.querySelectorAll(".right-wheels .speed-text").forEach((el) => {
    el.textContent = `${Math.abs(rightSpeed).toFixed(1)} RPM`;
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

  // TODO: add display of control speeds to html

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

  // Update command speed display periodically (user input feedback)
  setInterval(() => {
    updateRoverSpeedDisplay(); // Shows current command speeds
  }, 100);
});
