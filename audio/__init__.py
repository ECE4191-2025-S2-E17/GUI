from flask import Blueprint
from audio_classifier import AudioClassifier
from audio_reader import AudioReader
from queue import Queue
import atexit

AUDIO_URL = "http://192.168.5.98:81/audio"

audio_bp = Blueprint("audio", __name__)
# prevent memory leak by limiting the size of the queue
audio_chunk_queue = Queue(100)
audio_classification_result_queue = Queue(100)
audio_classifier = AudioClassifier(
    input_queue=audio_chunk_queue, output_queue=audio_classification_result_queue
)
audio_reader = AudioReader(
    audio_url=AUDIO_URL,
    queue=audio_chunk_queue,
)
audio_results = []
audio_reader.start()
audio_classifier.start()

atexit.register(audio_reader.stop)
atexit.register(audio_classifier.stop)
