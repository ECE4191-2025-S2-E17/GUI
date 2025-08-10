from flask import Flask, render_template, Response, jsonify
from camera import VideoCamera
import random
import time

app = Flask(__name__)
camera = VideoCamera()

@app.route('/')
def index():
    return render_template('index.html')

def generate_frames():
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/sensor_data')
def sensor_data():
    # Simulate sensor readings
    data = {
        "temperature": round(random.uniform(20, 25), 2),
        "humidity": round(random.uniform(40, 60), 2),
        "timestamp": int(time.time())
    }
    return jsonify(data)

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=5000, threaded=True)
    app.run(debug=True)
