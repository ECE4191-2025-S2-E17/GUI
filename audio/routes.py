from flask import Blueprint, jsonify
from . import audio_service  # Import the singleton instance

audio_bp = Blueprint("audio", __name__, url_prefix="/audio")


@audio_bp.route("/play")
def play_audio():
    audio_service.play()
    return jsonify({"status": "playing"})


@audio_bp.route("/pause")
def pause_audio():
    audio_service.pause()
    return jsonify({"status": "paused"})


@audio_bp.route("/start")
def start_classification():
    audio_service.start_classification()
    return jsonify({"status": "classification started"})


@audio_bp.route("/stop")
def stop_classification():
    audio_service.stop_classification()
    return jsonify({"status": "classification stopped"})
