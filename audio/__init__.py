from flask import Blueprint
from audio_classifier import AudioClassifier
from audio_reader import AudioReader

audio_bp = Blueprint("audio", __name__)
audio_classifier = AudioClassifier()
audio_reader = AudioReader()
