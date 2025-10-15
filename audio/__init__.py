from flask import Blueprint, current_app
from audio.audio_classifier import AudioClassifier
from audio.audio_reader import AudioReader
from audio.audio_recorder import AudioRecorder
from queue import Queue
import atexit
import os

# Create the blueprint with URL prefix
audio_bp = Blueprint("audio", __name__, url_prefix="/audio")

# Ensure audio_recordings folder exists
os.makedirs("audio_recordings", exist_ok=True)

# prevent memory leak by limiting the size of the queue
audio_chunk_queue = Queue(100)
audio_recording_queue = Queue(100)  # Separate queue for recording
audio_classification_result_queue = Queue(100)

audio_classifier = AudioClassifier(
    input_queue=audio_chunk_queue, result_queue=audio_classification_result_queue
)
audio_reader = AudioReader(
    audio_url=current_app.config["AUDIO_URL"],
    queue=audio_chunk_queue,
    recording_queue=audio_recording_queue,
)
audio_recorder = AudioRecorder(
    queue=audio_recording_queue, output_folder="audio_recordings"
)

audio_results = []
audio_reader.start()
audio_classifier.start()
audio_recorder.start()


def save_results():
    # Save the audio classification results to a file
    with open("audio_results.txt", "w") as f:
        for result in audio_results:
            f.write(f"{result}\n")


atexit.register(audio_reader.stop)
atexit.register(audio_classifier.stop)
atexit.register(audio_recorder.stop)
atexit.register(save_results)

# Import routes to register them with the blueprint
from audio import routes
