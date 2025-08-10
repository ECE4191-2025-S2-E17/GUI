import cv2

class VideoCamera:
    def __init__(self, source=0):
        self.video = cv2.VideoCapture(source)

    def get_frame(self):
        success, image = self.video.read()
        if not success:
            return b''

        # Encode frame as JPEG
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
