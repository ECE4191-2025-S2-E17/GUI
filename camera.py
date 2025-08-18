import cv2
import time
import os
import threading
from queue import Queue

os.makedirs("recordings", exist_ok=True)

class VideoCamera:
    def __init__(self, source=0):
        self.source = source
        self.video = self.connect()
        self.recording = False
        self.out = None

        # Frame queue for async recording
        self.record_queue = Queue(maxsize=100)
        self.record_thread = None
        self.stop_record_flag = False

    def connect(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            print("Could not connect")
        else:
            print("Connected to stream")
        return cap

    def reconnect(self):
        if self.video:
            self.video.release()
        time.sleep(1)
        self.video = self.connect()

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.recording: 
            return
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join("recordings", f"video_{timestamp}.mp4")

        width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.video.get(cv2.CAP_PROP_FPS) or 25  # safer default

        self.out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
        self.recording = True
        self.stop_record_flag = False

        # Start async thread
        self.record_thread = threading.Thread(target=self._record_worker, daemon=True)
        self.record_thread.start()
        print(f"Started recording: {filename}")

    def stop_recording(self):
        if not self.recording:
            return
        self.stop_record_flag = True
        self.recording = False
        self.record_thread.join()
        if self.out:
            self.out.release()
            self.out = None
        print("Stopped recording")

    def _record_worker(self):
        while not self.stop_record_flag or not self.record_queue.empty():
            try:
                frame = self.record_queue.get(timeout=0.1)
                if self.out:
                    self.out.write(frame)
            except:
                continue

    def get_frame(self):
        if not self.video or not self.video.isOpened():
            self.reconnect()

        success, image = self.video.read()
        if not success:
            self.reconnect()
            return b''

        # Queue frame for recording
        if self.recording and self.out:
            if not self.record_queue.full():
                self.record_queue.put_nowait(image)

        # Encode JPEG for live streaming
        _, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
