from flask import Flask, render_template, Response, jsonify, send_file
from camera import VideoCamera
import cv2
import time
import io



#IP_URL = "rtsp://118.139.84.194"
# IP_URL = "http://10.181.5.98/stream" 
IP_URL = 0

app = Flask(__name__)
camera = VideoCamera(IP_URL)



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

@app.route('/screenshot')
def screenshot():
    # Simulate sensor readings
    success, image = camera.video.read()
    cv2.imwrite('screenshot.jpg', image)
    return jsonify({"screenshot": "happened"})

@app.route('/record')
def toggle_recording():
    # Simulate sensor readings
    camera.toggle_recording()
    return jsonify({"recording": camera.recording})

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=5000, threaded=True)
    app.run(debug=True)
