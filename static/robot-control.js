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


function emergencyStop() {
    fetch(`${IP_URL}/emergency_stop`, { method: "POST" })
        .then(response => console.log("EMERGENCY STOP OK:", response.status))
        .catch(err => console.error("Emergency stop error:", err));
}
