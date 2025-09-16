from flask import (
    Flask,
    render_template,
    Response,
    jsonify,
)
from datetime import datetime
from camera import VideoCamera
import numpy as np
import cv2
import time
import random
#from audio import audio_bp
import os

VIDEO_URL = 0
AUDIO_URL = "http://192.168.107.98:82/audio"

camera = VideoCamera(VIDEO_URL)
app = Flask(__name__)
#app.register_blueprint(audio_bp)
os.makedirs("screenshots", exist_ok=True)

frame = None

# Debug: Print registered routes
with app.app_context():
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")


@app.route("/")
def index():
    return render_template("index.html")


def generate_frames():
    global frame
    while True:
        frame = camera.get_frame()

        # If frame is empty (camera disconnected), create placeholder
        if not frame:
            # Black image with "Disconnected" text
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(
                placeholder,
                "Disconnected",
                (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )
            _, frame = cv2.imencode(".jpg", placeholder)
            frame = frame.tobytes()

        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/screenshot", methods=["POST"])
def screenshot():
    global frame
    if frame is not None and len(frame) > 0:
        # Convert bytes to numpy array, then decode JPEG
        frame_array = np.frombuffer(frame, dtype=np.uint8)
        image = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

        if image is not None:
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"./screenshots/screenshot_{timestamp}.jpg"
            cv2.imwrite(filename, image)
            return f"<p>Screenshot saved as {filename}</p>"
        else:
            return "<p>Failed to decode image data</p>"
    else:
        return "<p>Failed to take screenshot - camera disconnected</p>"


@app.route("/record", methods=["POST"])
def toggle_recording():
    camera.toggle_recording()
    return render_template("partials/record_button.html", recording=camera.recording)

@app.route("/ai", methods=["POST"])
def toggle_ai():
    camera.toggle_ai()
    return render_template("partials/ai_button.html", ai_on=camera.ai_on)


@app.route("/status", methods=["GET"])
def get_status():
    camera_connected = camera.video and camera.video.isOpened()
    return render_template(
        "partials/status.html",
        recording=camera.recording,
        camera_connected=camera_connected,
        ai_on = camera.ai_on
    )


@app.route("/sightings", methods=["GET"])
def get_sightings():
    detections = camera.detections
    if not detections:
        return "<p>No recent sightings</p>"

    sightings_html = ""
    for detection in reversed(detections[-4:]):  # Show last 4 detections
        dt = datetime.fromtimestamp(detection['timestamp'])
        time_str = dt.strftime("%#I:%M")
        sightings_html += f"""
        <div style="border-bottom: 1px solid #333; padding: 5px 0;font-size: 0.8em;">
            <strong>{detection['class_name']}</strong><br>
            <small>Confidence: {detection['confidence']:.2f} | {dt.__str__()[:-7]}</small>
        </div>
        """
    return sightings_html


# Robot status endpoint for rover display
@app.route("/robot_status")
def robot_status():
    """Return current robot status including wheel speeds and height"""
    # TODO (figure out radius of wheels):
    wheel_radius = 0.1  # Example wheel radius in meters

    # Use wheel_radius and sent pwm to calculate linear speeds
    current_time = time.time()
    # TODO: Get actual wheel speeds from ESP32 or motor controllers
    # Example options:
    
    # Option 1: If you have global variables tracking current motor commands
    # left_speed = current_left_motor_pwm  # Replace with your actual variable
    # right_speed = current_right_motor_pwm  # Replace with your actual variable
    
    # Option 2: If you need to query ESP32 for current status
    # try:
    #     response = requests.get("http://192.168.5.129/status", timeout=1)
    #     data = response.json()
    #     left_speed = data.get('left_wheel', 0)
    #     right_speed = data.get('right_wheel', 0)
    # except:
    #     left_speed = 0
    #     right_speed = 0
    
    # Placeholder until you implement actual communication
    left_speed = 0
    right_speed = 0

    left_linear_speed = left_speed * wheel_radius  # m/s
    right_linear_speed = right_speed * wheel_radius  # m/s
    
    # Simulate height variation (replace with actual sensor data)
    # Range: 70-120mm, default around 72mm
    height = 72 + int(10 * np.sin(current_time * 0.2))  # Varies between 62-82mm
    height = max(70, min(120, height))  # Clamp between 70-120mm
    
    return jsonify({
        "wheels": {
            "left": left_speed,
            "right": right_speed
        },
        "height": height,
        "timestamp": current_time
    })


# Add new robot status endpoint for rover display
@app.route("/robot/status")
def robot_detailed_status():
    """Return detailed robot status for rover display"""
    current_time = time.time()
    
    # TODO: Get actual data from ESP32
    # For now, use simulated data
    
    # Simulate wheel speeds (in cm/s)
    left_wheel_speed = random.randint(0, 50) if random.random() > 0.7 else 0
    right_wheel_speed = random.randint(0, 50) if random.random() > 0.7 else 0
    
    # Simulate height variation (replace with actual sensor data)
    # Range: 70-120mm, default around 72mm
    height = 72 + int(15 * np.sin(current_time * 0.1))  # Varies between 57-87mm
    height = max(70, min(120, height))  # Clamp between 70-120mm
    
    return jsonify({
        "left_wheel_speed": left_wheel_speed,
        "right_wheel_speed": right_wheel_speed,
        "height": height,
        "battery_level": random.randint(60, 100),  # Simulate battery
        "connection_status": "connected",
        "timestamp": current_time
    })


# Drive command endpoint to integrate with ESP32
@app.route("/drive")
def drive_command():
    """Handle drive commands and forward to ESP32"""
    from flask import request
    
    direction = request.args.get('direction', 'stop')
    speed = int(request.args.get('speed', 0))
    
    # Convert to ESP32 wheel commands (lw, rw format)
    left_wheel = 0
    right_wheel = 0
    
    if direction == "forward":
        left_wheel = speed
        right_wheel = speed
    elif direction == "backward":
        left_wheel = -speed
        right_wheel = -speed
    elif direction == "left":
        left_wheel = -speed
        right_wheel = speed
    elif direction == "right":
        left_wheel = speed
        right_wheel = -speed
    
    # TODO: Send commands to ESP32 here
    # Example: requests.get(f"http://192.168.5.129/drive?lw={left_wheel}&rw={right_wheel}")
    
    print(f"Drive command: {direction} at {speed}% -> lw={left_wheel}, rw={right_wheel}")
    
    return jsonify({
        "status": "success",
        "direction": direction,
        "speed": speed,
        "wheels": {
            "left": left_wheel,
            "right": right_wheel
        }
    })


# Height control endpoints
@app.route("/height/up")
def height_up():
    """Increase robot height"""
    # TODO: Send height up command to ESP32
    print("Height UP command received")
    
    return jsonify({
        "status": "success",
        "action": "height_up",
        "command": "Q key pressed"
    })


@app.route("/height/down")
def height_down():
    """Decrease robot height"""
    # TODO: Send height down command to ESP32
    print("Height DOWN command received")
    
    return jsonify({
        "status": "success",
        "action": "height_down",
        "command": "E key pressed"
    })


if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=5000, threaded=True)
    app.run(debug=True, use_reloader=False)