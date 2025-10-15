from flask import Blueprint, current_app, json
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


def summarize_results(results):
    summary_dict = {}
    for result in results:
        name, confidence = result.get("name", "Unknown"), result.get("confidence", 0.0)
        summary_dict.setdefault(name, {"count": 0, "total_confidence": 0.0})
        # for each name, find number of occurrences and average confidence
        summary_dict[name]["count"] += 1
        summary_dict[name]["total_confidence"] += confidence
        summary_dict[name]["average_confidence"] = (
            summary_dict[name]["total_confidence"] / summary_dict[name]["count"]
        )
    summary_dict = dict(
        sorted(summary_dict.items(), key=lambda x: x[1]["count"], reverse=True)
    )
    return summary_dict

def save_results():
    # Save the audio classification results to a file
    with open("audio_results.txt", "w") as f:
        for result in audio_results:
            f.write(f"{result}\n")

    with open("audio_results_summary.json", "w") as f:
        json.dump(summarize_results(audio_results), f, indent=2)


atexit.register(audio_reader.stop)
atexit.register(audio_classifier.stop)
atexit.register(audio_recorder.stop)
atexit.register(save_results)

# Import routes to register them with the blueprint
from audio import routes

if __name__ == "__main__":
    with open("audio_results.txt", "r") as f:
        for line in f:
            audio_results.append(json.loads(line.strip()))
    audio_results_summary = summarize_results(audio_results)
    with open("audio_results_summary.json", "w") as f:
        json.dump(audio_results_summary, f, indent=2)
    
