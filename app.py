from flask import (
    Flask,
    render_template,
    Response,
    stream_template,
)
from camera import VideoCamera
import numpy as np
import cv2
import time
import json
from audio import audio_bp
from drive import drive_bp
from status import status_bp, status_manager
import os

VIDEO_URL = "http://192.168.107.98:81/stream"
AUDIO_URL = "http://192.168.107.98:82/audio"

camera = VideoCamera(VIDEO_URL)
app = Flask(__name__)
app.register_blueprint(audio_bp)
app.register_blueprint(drive_bp)
app.register_blueprint(status_bp)
os.makedirs("screenshots", exist_ok=True)

frame = None

# Initialize status
def update_camera_status():
    """Update camera and recording status"""
    camera_connected = camera.video and camera.video.isOpened()
    recording = camera.recording
    status_manager.update_status(
        camera_connected=camera_connected,
        recording=recording
    )

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
    update_camera_status()  # Notify status change
    return render_template("partials/record_button.html", recording=camera.recording)


@app.route("/status", methods=["GET"])
def get_status():
    camera_connected = camera.video and camera.video.isOpened()
    return render_template(
        "partials/status.html",
        recording=camera.recording,
        camera_connected=camera_connected,
    )


@app.route("/sightings", methods=["GET"])
def get_sightings():
    detections = camera.latest_detections
    if not detections:
        return "<p>No recent sightings</p>"

    sightings_html = ""
    for detection in detections[-5:]:  # Show last 5 detections
        sightings_html += f"""
        <div style="border-bottom: 1px solid #333; padding: 5px 0;">
            <strong>{detection['class_name']}</strong><br>
            <small>Confidence: {detection['confidence']:.2f} | {detection['timestamp']}</small>
        </div>
        """
    return sightings_html


if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=5000, threaded=True)
    app.run(debug=True, use_reloader=False)
