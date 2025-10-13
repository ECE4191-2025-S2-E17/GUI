import threading
import queue
import requests
import numpy as np
import pyaudio
import time

from audio.constants import CLIP_SIZE, STEP_SIZE, TARGET_SAMPLING_RATE_HZ


# Maybe offering audio cleaning here as well.
class AudioReader(threading.Thread):
    def __init__(
        self,
        audio_url: str,
        queue: queue.Queue,
        max_retries: int = 5,
        retry_delay: float = 2.0,
    ) -> None:
        super().__init__(daemon=True)
        if not audio_url:
            raise ValueError("audio_url must be provided")
        self.buffer = np.array([], dtype="<i2")  # Fixed data type
        self.pyaudio_stream = pyaudio.PyAudio().open(
            format=pyaudio.paInt16,
            channels=1,
            rate=TARGET_SAMPLING_RATE_HZ,
            output=True,
        )
        self.audio_url = audio_url
        self.running = False
        self.queue = queue
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0

    def stop(self):
        self.running = False

    def pause_stream(self):
        if self.pyaudio_stream.is_active():
            self.pyaudio_stream.stop_stream()

    def resume_stream(self):
        if not self.pyaudio_stream.is_active():
            self.pyaudio_stream.start_stream()

    def run(self):
        self.running = True

        while self.running and self.retry_count <= self.max_retries:
            try:
                print(
                    f"Connecting to audio stream: {self.audio_url} (attempt {self.retry_count + 1}/{self.max_retries + 1})"
                )
                with requests.get(self.audio_url, stream=True, timeout=10) as response:
                    response.raise_for_status()
                    print(f"Successfully connected to audio stream: {self.audio_url}")
                    self.retry_count = 0  # Reset retry count on successful connection

                    # 10ms of audio at 32kHz, 32-bit int
                    for chunk in response.iter_content(chunk_size=320):
                        if not self.running:
                            return

                        sample_32 = np.frombuffer(chunk, dtype="<i4")
                        sample_24 = sample_32 >> 8
                        sample_16 = (sample_24 >> 8).astype(np.int16)

                        self.buffer = np.concatenate((self.buffer, sample_16))

                        if self.pyaudio_stream.is_active():
                            self.pyaudio_stream.write(sample_16.tobytes())
                        if self.buffer.size >= CLIP_SIZE:
                            self.queue.put(self.buffer[:CLIP_SIZE])
                            self.buffer = self.buffer[STEP_SIZE:]

            except requests.RequestException as e:
                self.retry_count += 1
                if self.retry_count <= self.max_retries:
                    print(
                        f"Audio stream error (attempt {self.retry_count}/{self.max_retries + 1}): {e}"
                    )
                    print(f"Retrying in {self.retry_delay} seconds...")
                    if self.running:
                        time.sleep(self.retry_delay)
                else:
                    print(
                        f"Max retries ({self.max_retries}) exceeded. Stopping audio reader."
                    )
                    break
            except Exception as e:
                print(f"Unexpected error in audio reader: {e}")
                break

        self.running = False
        print("Audio reader stopped")


if __name__ == "__main__":
    # Start audio reader thread
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16, channels=1, rate=TARGET_SAMPLING_RATE_HZ, output=True
    )
    data_queue = queue.Queue()
    audio_reader = AudioReader(
        audio_url="http://192.168.5.98:82/audio", queue=data_queue
    )
    audio_reader.start()

    try:
        while audio_reader.is_alive():
            audio_reader.join(timeout=0.1)

    except KeyboardInterrupt:
        print("Stopping audio reader...")
        audio_reader.stop()
        audio_reader.join(timeout=2)
    finally:
        # from matplotlib import pyplot as plt
        # if not data_queue.empty():
        #     data = data_queue.get()
        #     plt.plot(data)
        # plt.show()
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("Cleanup completed")
