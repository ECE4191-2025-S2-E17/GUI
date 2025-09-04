from flask import (
    Flask,
    render_template,
    Response,
    jsonify,
    current_app,
    render_template_string,
)
from camera import VideoCamera
import numpy as np
import cv2
import time
import io

VIDEO_URL = "http://192.168.5.98:81/stream"
AUDIO_URL = "http://192.168.5.98:81/audio"

camera = VideoCamera(VIDEO_URL)
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


def generate_frames():
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
    # Simulate sensor readings
    success, image = camera.video.read()
    if success:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.imwrite("screenshot.jpg", image)
        return f"<p>Screenshot taken at {timestamp}</p>"
    else:
        return "<p>Failed to take screenshot - camera disconnected</p>"


@app.route("/record", methods=["POST"])
def toggle_recording():
    camera.toggle_recording()
    return render_template("partials/record_button.html", recording=camera.recording)


@app.route("/status", methods=["GET"])
def get_status():
    camera_connected = camera.video and camera.video.isOpened()
    return render_template(
        "partials/status.html",
        recording=camera.recording,
        camera_connected=camera_connected,
    )


@app.route("/toggle_audio", methods=["POST"])
def toggle_audio():
    # For now, just return a placeholder since audio functionality isn't implemented
    return "<p>Audio toggle not implemented yet</p>"


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
