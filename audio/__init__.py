from flask import Blueprint, current_app
from audio.audio_classifier import AudioClassifier
from audio.audio_reader import AudioReader
from queue import Queue
import atexit

# Create the blueprint with URL prefix
audio_bp = Blueprint("audio", __name__, url_prefix="/audio")

# prevent memory leak by limiting the size of the queue
audio_chunk_queue = Queue(100)
audio_classification_result_queue = Queue(100)
audio_classifier = AudioClassifier(
    input_queue=audio_chunk_queue, result_queue=audio_classification_result_queue
)
audio_reader = AudioReader(
    audio_url=current_app.config["AUDIO_URL"],
    queue=audio_chunk_queue,
)
audio_results = []
audio_reader.start()
audio_classifier.start()


def save_results():
    # Save the audio classification results to a file
    with open("audio_results.txt", "w") as f:
        for result in audio_results:
            f.write(f"{result}\n")


atexit.register(audio_reader.stop)
atexit.register(audio_classifier.stop)
atexit.register(save_results)

# Import routes to register them with the blueprint
from audio import routes
