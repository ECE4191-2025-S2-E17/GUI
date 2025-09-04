from flask import Blueprint, jsonify
from audio import audio_classifier, audio_reader, audio_results

audio_bp = Blueprint("audio", __name__, url_prefix="/audio")


@audio_bp.route("/play")
def play_audio():
    audio_reader.resume_stream()
    return jsonify({"status": "playing"})


@audio_bp.route("/pause")
def pause_audio():
    audio_reader.pause_stream()
    return jsonify({"status": "paused"})


@audio_bp.route("/clear_buffer")
def start_classification():
    audio_classifier.clear_buffer()
    return jsonify({"status": "classification started"})


@audio_bp.route("/results")
def stop_classification():
    while not audio_classifier.result_queue.empty():
        audio_results.append(audio_classifier.result_queue.get())
    return jsonify({"results": audio_results})
