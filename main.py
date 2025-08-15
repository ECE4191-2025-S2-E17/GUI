import sys
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsDropShadowEffect
from PyQt5.QtGui import QImage, QPixmap, QColor
from PyQt5.QtCore import QTimer
from ui_main import Ui_MainWindow 

IP_URL = "rtsp://10.0.0.211"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setup UI from Designer
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Using webcam for now
        self.video_feed = cv2.VideoCapture(IP_URL) 
        # self.video_feed = cv2.VideoCapture("video_path.mp4") # Can use a video file instead, will be very fast for now


        # Set up shadow effect for the video display
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.ui.Video.setGraphicsEffect(shadow)

        # Set the window title
 

        # Create timer to update frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ms = ~33 fps

  

    def update_frame(self):
        ret, frame = self.video_feed.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            #self.ui.listWidget.addItem("Species: Kangaroo")


            
            self.ui.Video.setPixmap(pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
