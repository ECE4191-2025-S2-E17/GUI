import threading
import queue
from typing import Optional
import numpy as np
import wave
import os
from datetime import datetime
from audio.constants import TARGET_SAMPLING_RATE_HZ


class AudioRecorder(threading.Thread):
    """Records audio chunks to a WAV file until stopped."""

    def __init__(
        self,
        queue: queue.Queue,
        output_folder: str = "audio_recordings",
        output_file: Optional[str] = None,
    ) -> None:
        super().__init__(daemon=True)
        self.queue = queue
        self.output_folder = output_folder
        self.running = False
        self.wav_writer = None

        # Create output folder if it doesn't exist
        os.makedirs(self.output_folder, exist_ok=True)

        # Generate filename with timestamp
        if output_file:
            self.output_file = os.path.join(self.output_folder, output_file)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file: str = os.path.join(
                self.output_folder, f"audio_recording_{timestamp}.wav"
            )

    def stop(self):
        """Stop recording and close the file."""
        self.running = False
        print(f"Audio recording stopped. File saved: {self.output_file}")

    def run(self):
        """Main recording loop - writes audio chunks to WAV file."""
        self.running = True

        # Open WAV file for writing
        self.wav_writer = wave.open(self.output_file, "wb")
        self.wav_writer.setnchannels(1)  # Mono
        self.wav_writer.setsampwidth(2)  # 16-bit (2 bytes)
        self.wav_writer.setframerate(TARGET_SAMPLING_RATE_HZ)

        print(f"Audio recording started: {self.output_file}")

        try:
            while self.running:
                try:
                    # Get audio chunk with timeout to allow checking running flag
                    audio_chunk = self.queue.get(timeout=0.5)

                    # Convert numpy array to bytes and write to WAV file
                    if isinstance(audio_chunk, np.ndarray):
                        audio_bytes = audio_chunk.astype(np.int16).tobytes()
                        self.wav_writer.writeframes(audio_bytes)

                except queue.Empty:
                    # No data available, continue loop
                    continue
                except Exception as e:
                    print(f"Error writing audio chunk: {e}")

        finally:
            # Close WAV file
            if self.wav_writer:
                self.wav_writer.close()
            print(f"Audio recording saved to: {self.output_file}")
