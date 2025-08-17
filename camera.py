import cv2
import time
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"  


class VideoCamera:
    def __init__(self, source=0):
        self.source = source
        self.video = self.connect()
        self.recording = False

        self.out = None

        
        
    def toggle_recording(self):
        """Externally called to start/stop recording"""
        self.recording = not self.recording

        if self.recording:
            # Start a new file
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = os.path.join(f"recordings/video_{timestamp}.mp4")

            width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.video.get(cv2.CAP_PROP_FPS) or 10  # default to 10 if unknown

            self.out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
            print(f"Started recording: {filename}")
        else:
            # Stop recording and finalize file
            if self.out:
                self.out.release()
                self.out = None
                print("Stopped recording")



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

        # Check if disconnected
        if not self.video or not self.video.isOpened():
            self.reconnect()


        success, image = self.video.read()
        if not success:
            self.reconnect()
            return b''

        # Store if recording
        if self.recording and self.out:
            self.out.write(image)
       
        # Encode frame as JPEG
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
