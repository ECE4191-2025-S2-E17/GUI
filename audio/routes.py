from flask import render_template
from audio import audio_classifier, audio_reader, audio_results, audio_bp

audio_playing = True


@audio_bp.route("/toggle", methods=["POST"])
def toggle_audio():
    global audio_playing
    if audio_playing:
        # Currently playing, so pause it
        audio_reader.pause_stream()
        audio_classifier.pause()
        audio_playing = False
    else:
        # Currently paused, so play it
        audio_reader.resume_stream()
        audio_classifier.resume()
        audio_playing = True

    return render_template("partials/audio_toggle.html", playing=audio_playing)


@audio_bp.route("/sightings")
def get_audio_sightings():
    # Get the latest audio classification results
    latest_results = []
    while not audio_classifier.result_queue.empty():
        queue_item = audio_classifier.result_queue.get()

        # Handle both old format (just logits) and new format (logits, timestamp)
        if isinstance(queue_item, tuple):
            logits, timestamp = queue_item
        else:
            logits = queue_item
            timestamp = None

        result = audio_classifier.get_result(logits, timestamp=timestamp)
        if result["name"] in ["Noise", "Water", "Nothing"]:
            continue
        print(f"Audio classification result: {result}")
        audio_results.append(result)
        latest_results.append(result)

    # Get the most recent results (last 3)
    recent_results = (latest_results + audio_results)[-3:]

    if not recent_results:
        return "<p>No audio classifications yet<br><small>Start audio streaming to see results</small></p>"

    sightings_html = ""
    for i, result in enumerate(recent_results):
        class_name = result.get("name", "Unknown")
        confidence = result.get("confidence", 0.0)
        timestamp = result.get("timestamp", None)

        timestamp_str = (
            f"<small>Time: {timestamp:.1f}s</small><br>"
            if timestamp is not None
            else ""
        )

        sightings_html += f"""
        <div style="border-bottom: 1px solid #333; padding: 5px 0; font-size: 0.8em;">
            <strong>🔊 {class_name}</strong><br>
            {timestamp_str}
            <small>Confidence: {confidence:.2f}</small>
        </div>
        """
    return sightings_html
