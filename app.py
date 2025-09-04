from flask import Flask, render_template, Response, jsonify, current_app
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


@app.route("/screenshot")
def screenshot():
    # Simulate sensor readings
    success, image = camera.video.read()
    cv2.imwrite("screenshot.jpg", image)
    return jsonify({"screenshot": "happened"})


@app.route("/record")
def toggle_recording():
    # Simulate sensor readings
    camera.toggle_recording()
    return jsonify({"recording": camera.recording})


@app.route("/toggle_audio")
def toggle_audio():
    # Simulate sensor readings
    camera.toggle_audio()
    return jsonify({"audio": camera.audio_enabled})


if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=5000, threaded=True)
    app.run(debug=True, use_reloader=False)
