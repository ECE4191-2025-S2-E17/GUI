const IP_URL = "http://192.168.107.98"; 

let speed = 100; 


function highlightKey(id, active) {
    const key = document.getElementById(id);
    if (key) {
        key.classList.toggle("active", active);
    }
}


document.addEventListener("keydown", function(event) {
    switch (event.key) {
        // Drive
        case "w":
            highlightKey("key-w", true);
            sendDriveCommand("forward", speed);
            break;
        case "s":
            highlightKey("key-s", true);
            sendDriveCommand("backward", speed);
            break;
        case "a":
            highlightKey("key-a", true);
            sendDriveCommand("left", speed);
            break;
        case "d":
            highlightKey("key-d", true);
            sendDriveCommand("right", speed);
            break;

        // Gimbal (Arrow keys)
        case "ArrowLeft":
            highlightKey("key-left", true);
            sendGimbalCommand(-10, 0);
            break;
        case "ArrowRight":
            highlightKey("key-right", true);
            sendGimbalCommand(10, 0);
            break;
        case "ArrowUp":
            highlightKey("key-up", true);
            sendGimbalCommand(0, 10);
            break;
        case "ArrowDown":
            highlightKey("key-down", true);
            sendGimbalCommand(0, -10);
            break;

        // Height controls
        case "q":
        case "Q":
            highlightKey("key-q", true);
            sendHeightCommand("up");
            break;
        case "e":
        case "E":
            highlightKey("key-e", true);
            sendHeightCommand("down");
            break;

        // Emergency stop
        case " ":
            highlightKey("key-space", true);
            sendDriveCommand("stop", 0);
            break;
    }
});


document.addEventListener("keyup", function(event) {
    switch (event.key) {
        // Drive keys
        case "w":
        case "s":
        case "a":
        case "d":
            highlightKey("key-" + event.key, false);
            sendDriveCommand("stop", 0);  
            break;

        // Gimbal keys
        case "ArrowLeft":
            highlightKey("key-left", false);
            sendGimbalCommand(0, 0);
            break;
        case "ArrowRight":
            highlightKey("key-right", false);
            sendGimbalCommand(0, 0);
            break;
        case "ArrowUp":
            highlightKey("key-up", false);
            sendGimbalCommand(0, 0);
            break;
        case "ArrowDown":
            highlightKey("key-down", false);
            sendGimbalCommand(0, 0);
            break;

        // Height keys
        case "q":
        case "Q":
            highlightKey("key-q", false);
            break;
        case "e":
        case "E":
            highlightKey("key-e", false);
            break;

        // Spacebar
        case " ":
            highlightKey("key-space", false);
            break;
    }
});


// Send HTTP
function sendDriveCommand(direction, speed) {
    fetch(`${IP_URL}/drive?direction=${direction}&speed=${speed}`)
        .then(response => console.log("Drive OK:", response.status))
        .catch(err => console.error("Drive error:", err));
}


function sendGimbalCommand(pan, tilt) {
    fetch(`${IP_URL}/gimbal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pan: pan, tilt: tilt })
    })
    .then(response => console.log("Gimbal OK:", response.status))
    .catch(err => console.error("Gimbal error:", err));
}


function sendHeightCommand(direction) {
    const endpoint = direction === "up" ? "/height/up" : "/height/down";
    fetch(`${IP_URL}${endpoint}`)
        .then(response => response.json())
        .then(data => {
            console.log("Height command OK:", data);
            updateHeightDisplay(); // Update the height display after command
        })
        .catch(err => console.error("Height command error:", err));
}


function emergencyStop() {
    fetch(`${IP_URL}/emergency_stop`, { method: "POST" })
        .then(response => console.log("EMERGENCY STOP OK:", response.status))
        .catch(err => console.error("Emergency stop error:", err));
}


// Height display functions
function updateHeightDisplay() {
    fetch(`${IP_URL}/robot/status`)
        .then(response => response.json())
        .then(data => {
            const heightNumber = document.getElementById('height-number');
            const heightFill = document.getElementById('height-fill');
            const heightIndicator = document.getElementById('height-indicator');
            
            if (heightNumber && heightFill && heightIndicator) {
                const height = data.height || 72; // Default to 72mm
                const minHeight = 70; // Minimum height 70mm
                const maxHeight = 120; // Maximum height 120mm
                
                // Update number display
                heightNumber.textContent = height;
                
                // Calculate percentage for bar fill
                const percentage = ((height - minHeight) / (maxHeight - minHeight)) * 100;
                heightFill.style.height = `${Math.max(0, Math.min(100, percentage))}%`;
                
                // Update indicator position
                const indicatorTop = 100 - percentage;
                heightIndicator.style.top = `${Math.max(0, Math.min(100, indicatorTop))}%`;
            }
        })
        .catch(err => console.error("Height update error:", err));
}

// Rover speed display functions
function updateRoverDisplay() {
    fetch(`${IP_URL}/robot/status`)
        .then(response => response.json())
        .then(data => {
            // Update wheel speeds
            const leftSpeed = data.left_wheel_speed || 0;
            const rightSpeed = data.right_wheel_speed || 0;
            
            // Update speed displays
            document.querySelectorAll('.left-wheels .speed-text').forEach(el => {
                el.textContent = `${Math.abs(leftSpeed)} cm/s`;
            });
            document.querySelectorAll('.right-wheels .speed-text').forEach(el => {
                el.textContent = `${Math.abs(rightSpeed)} cm/s`;
            });
            
            // Update wheel indicators
            document.querySelectorAll('.left-wheels .wheel').forEach(wheel => {
                wheel.classList.toggle('active', leftSpeed !== 0);
            });
            document.querySelectorAll('.right-wheels .wheel').forEach(wheel => {
                wheel.classList.toggle('active', rightSpeed !== 0);
            });
        })
        .catch(err => console.error("Rover display update error:", err));
}

// Initialize displays when page loads
document.addEventListener('DOMContentLoaded', function() {
    updateHeightDisplay();
    updateRoverDisplay();
    
    // Update displays periodically
    setInterval(() => {
        updateHeightDisplay();
        updateRoverDisplay();
    }, 1000); // Update every second
});
