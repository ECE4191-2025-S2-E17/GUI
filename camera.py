import cv2
import time
import os
import threading
import numpy as np
from queue import Queue
from ultralytics import YOLO

os.makedirs("recordings", exist_ok=True)
animal_emojis = {
    0: "🦜",  # Cockatoo (parrot emoji as closest)
    1: "🐊",  # Crocodile
    2: "🐸",  # Frog
    3: "🦘",  # Kangaroo
    4: "🐨",  # Koala
    5: "🦆",  # Platypus (no platypus emoji, use duck or similar)
    6: "😈",  # Tasdevil (no emoji, using devil face as playful substitute)
    7: "🐻‍❄️",  # Wombat (no wombat emoji, using bear as closest)
}


class VideoCamera:
    FRAME_PER_CLASSIFICATION = 1

    def __init__(self, source=0):
        self.source = source
        # Initialise model
        self.model = YOLO("best.pt", verbose=False)
        self.ai_on = False
        self.video = None  # Start with None, will connect on first frame request
        self.recording = False
        self.out = None
        self.detections = []
        self.latest_detections = []
        self.frame_since_last_detection = 0

        self.manual_classification = True

        # Frame queue for async recording
        self.record_queue = Queue(maxsize=100)
        self.record_thread = None
        self.stop_record_flag = False

        # Connection retry tracking
        self.last_connection_attempt = 0
        self.connection_retry_delay = 5  # seconds between retry attempts
        self.connection_in_progress = False

        # Start initial connection attempt in background thread
        print(f"Starting background connection to video source: {source}")
        self._start_connection_thread()

    def _get_placeholder_frame(self):
        """Return a placeholder frame when camera is not available"""
        # Create a black image with text
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)

        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text1 = "Camera Disconnected"
        text2 = f"Retrying connection to: {self.source}"
        text3 = "Please wait..."

        cv2.putText(
            placeholder, text1, (120, 200), font, 1, (0, 0, 255), 2, cv2.LINE_AA
        )
        cv2.putText(
            placeholder, text2, (60, 250), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA
        )
        cv2.putText(
            placeholder, text3, (220, 290), font, 0.7, (255, 255, 255), 1, cv2.LINE_AA
        )

        # Encode to JPEG
        _, jpeg = cv2.imencode(".jpg", placeholder)
        return jpeg.tobytes()

    def _start_connection_thread(self):
        """Start a background thread to connect to the camera"""
        if not self.connection_in_progress:
            self.connection_in_progress = True
            connection_thread = threading.Thread(
                target=self._connect_background, daemon=True
            )
            connection_thread.start()

    def _connect_background(self):
        """Background thread function to connect to camera"""
        try:
            self.connect()
        finally:
            self.connection_in_progress = False

    def connect(self):
        try:
            self.last_connection_attempt = time.time()
            video = cv2.VideoCapture(self.source)

            # Set timeout for network streams (in milliseconds)
            if isinstance(self.source, str) and (
                self.source.startswith("http") or self.source.startswith("rtsp")
            ):
                video.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)  # 3 second timeout
                video.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)

            if not video.isOpened():
                print(f"✗ Failed to open video source: {self.source}")
                try:
                    video.release()
                except:
                    pass
                return None
            print(f"✓ Successfully connected to video source: {self.source}")
            self.video = video
            return video
        except Exception as e:
            print(f"✗ Error connecting to video source: {e}")
            return None

    def reconnect(self):
        # Check if enough time has passed since last attempt
        current_time = time.time()
        if current_time - self.last_connection_attempt < self.connection_retry_delay:
            return False

        # Don't start a new connection if one is already in progress
        if self.connection_in_progress:
            return False

        print(f"Scheduling reconnection to video source...")
        if self.video:
            try:
                self.video.release()
                self.video = None
            except:
                pass

        # Start connection in background thread
        self._start_connection_thread()
        return False  # Return False since connection is async

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def toggle_ai(self):
        self.ai_on = not self.ai_on

    def start_recording(self):
        if self.recording:
            return

        # Cannot record if video is not connected
        if not self.video or not self.video.isOpened():
            print("Cannot start recording - camera not connected")
            return

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
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
        print(self.recording)
        if self.record_thread:
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
            # Try to reconnect (respects retry delay)
            self.reconnect()

            # If still not connected, return placeholder frame
            if not self.video or not self.video.isOpened():
                return self._get_placeholder_frame()

        try:
            success, image = self.video.read()
            if not success:
                self.reconnect()
                if not self.video or not self.video.isOpened():
                    return self._get_placeholder_frame()

                success, image = self.video.read()
                if not success:
                    return self._get_placeholder_frame()
        except Exception as e:
            print(f"Error reading frame: {e}")
            return self._get_placeholder_frame()

        # Rotate frame 90 degrees clockwise
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

        # Queue frame for recording
        if self.recording and self.out:
            if not self.record_queue.full():
                self.record_queue.put_nowait(image)

        # Encode JPEG for live streaming
        _, jpeg = cv2.imencode(".jpg", image)

        if self.ai_on:
            self.frame_since_last_detection += 1
            if self.frame_since_last_detection < self.FRAME_PER_CLASSIFICATION:
                return jpeg.tobytes()
            self.frame_since_last_detection = 0

            results = self.model(image, verbose=False)

            # --- Deduplicated detections ---
            MAX_AGE = 5  # seconds to keep a detection alive
            IOU_THRESHOLD = 0.5  # overlap threshold to consider same object

            def iou(box1, box2):
                x1 = max(box1[0], box2[0])
                y1 = max(box1[1], box2[1])
                x2 = min(box1[2], box2[2])
                y2 = min(box1[3], box2[3])
                inter_area = max(0, x2 - x1) * max(0, y2 - y1)
                area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
                area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
                if area1 + area2 - inter_area == 0:
                    return 0
                return inter_area / (area1 + area2 - inter_area)

            current_time = time.time()
            # Remove old detections
            self.latest_detections = [
                s
                for s in self.latest_detections
                if current_time - s["timestamp"] < MAX_AGE
            ]

            if results and len(results) > 0 and not self.manual_classification:
                for r in results[0].boxes:
                    conf = float(r.conf.cpu().numpy()[0])
                    if conf > 0.7:  # confidence threshold
                        class_id = int(r.cls.cpu().numpy()[0])
                        class_name = (
                            self.model.names[class_id]
                            if class_id < len(self.model.names)
                            else f"Class_{class_id}"
                        )
                        bbox = r.xyxy.cpu().numpy()[0]  # x1,y1,x2,y2

                        # Check for duplicates
                        duplicate = False
                        for s in self.latest_detections:
                            if (
                                s["class_name"]
                                == f"{animal_emojis[class_id]} {class_name}"
                                and iou(bbox, s["bbox"]) > IOU_THRESHOLD
                            ):
                                duplicate = True
                                break

                        if not duplicate:
                            self.latest_detections.append(
                                {
                                    "class_name": f"{animal_emojis[class_id]} {class_name}",
                                    "confidence": conf,
                                    "bbox": bbox,
                                    "timestamp": current_time,
                                }
                            )
                            self.detections.append(
                                {
                                    "class_name": f"{animal_emojis[class_id]} {class_name}",
                                    "confidence": conf,
                                    "timestamp": current_time,
                                }
                            )

            img = results[0].plot()
            _, jpeg = cv2.imencode(".jpg", img)

        return jpeg.tobytes()

    def manual_classify(self, image):
        """
        Manually classify the given image (numpy array) using YOLO.
        Returns a list of detections added.
        """
        results = self.model(image, verbose=False)
        if not results or len(results) == 0:
            return []

        current_time = time.time()
        detections_added = []

        for r in results[0].boxes:
            conf = float(r.conf.cpu().numpy()[0])
            if conf > 0.7:
                class_id = int(r.cls.cpu().numpy()[0])
                class_name = (
                    self.model.names[class_id]
                    if class_id < len(self.model.names)
                    else f"Class_{class_id}"
                )
                self.detections.append(
                    {
                        "class_name": f"{animal_emojis[class_id]} {class_name}",
                        "confidence": conf,
                        "timestamp": current_time,
                    }
                )
                detections_added.append(
                    {
                        "class_name": f"{animal_emojis[class_id]} {class_name}",
                        "confidence": conf,
                    }
                )

        return detections_added

        pass
