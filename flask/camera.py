import cv2
import time
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"  


class VideoCamera:
    def __init__(self, source=0):
        self.source = source
        self.video = self.connect()
        self.recording = False
        


    def connect(self):
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                print(f"Could not connect")
            else:
                print(f"Connected to stream")
            return cap
    
    def reconnect(self):
        """Close old capture and try to reconnect."""
        if self.video:
            self.video.release()
        time.sleep(1)
        self.video = self.connect()

    def get_frame(self):

        if not self.video or not self.video.isOpened():
            self.reconnect()


        success, image = self.video.read()
        if not success:
            self.reconnect()
            return b''

       
        # Encode frame as JPEG
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
