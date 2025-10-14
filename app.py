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

# from audio import audio_bp
import os

ESP_IP = "192.168.137.25"
VIDEO_URL = f"http://{ESP_IP}:81/stream"
AUDIO_URL = f"http://{ESP_IP}:83/audio"

camera = VideoCamera(VIDEO_URL, ESP_IP)
app = Flask(__name__)
app.config["AUDIO_URL"] = AUDIO_URL
app.config["VIDEO_URL"] = VIDEO_URL
# app.register_blueprint(audio_bp)
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


@app.route("/env.js")
def env_js():
    js_content = f"""
    window.env = {{
        ESP_IP: "{ESP_IP}",
    }};
    """
    return Response(js_content, mimetype="application/javascript")


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

            if camera.manual_classification:
                detections = camera.manual_classify(image)
                if detections:
                    det_text = "<br>".join(
                        [
                            f"{d['class_name']} (conf: {d['confidence']:.2f})"
                            for d in detections
                        ]
                    )
                    return f"<p>Screenshot saved and classified:<br>{det_text}</p>"

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
        ai_on=camera.ai_on,
    )


@app.route("/sightings", methods=["GET"])
def get_sightings():
    detections = camera.detections
    if not detections:
        return "<p>No recent sightings</p>"

    sightings_html = ""
    for detection in reversed(detections[-4:]):  # Show last 4 detections
        dt = datetime.fromtimestamp(detection["timestamp"])
        time_str = dt.strftime("%#I:%M")
        sightings_html += f"""
        <div style="border-bottom: 1px solid #333; padding: 5px 0;font-size: 0.8em;">
            <strong>{detection['class_name']}</strong><br>
            <small>Confidence: {detection['confidence']:.2f} | {dt.__str__()[:-7]}</small>
        </div>
        """
    return sightings_html


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True)
