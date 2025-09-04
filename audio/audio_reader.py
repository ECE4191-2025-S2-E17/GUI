import threading
import queue
import requests
import numpy as np
import pyaudio

from audio.constants import CLIP_SIZE, STEP_SIZE, TARGET_SAMPLING_RATE_HZ


# Maybe offering audio cleaning here as well.
class AudioReader(threading.Thread):
    def __init__(self, audio_url: str, queue: queue.Queue) -> None:
        super().__init__(daemon=True)
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
        try:
            with requests.get(self.audio_url, stream=True, timeout=10) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=4096):
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
            print(f"Error occurred: {e}")
        finally:
            self.running = False


if __name__ == "__main__":
    # Start audio reader thread
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16, channels=1, rate=TARGET_SAMPLING_RATE_HZ, output=True
    )
    data_queue = queue.Queue()
    audio_reader = AudioReader(
        esp_ip="192.168.5.98", pyaudio_stream=stream, queue=data_queue
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
