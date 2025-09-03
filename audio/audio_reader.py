import threading
import queue
import requests
import numpy as np
import pyaudio
from pyaudio import Stream


# Maybe offering audio cleaning here as well. 
class AudioReader(threading.Thread):
    SAMPLING_RATE = 22050
    CLASSIFICATION_DURATION = 2

    def __init__(self, esp_ip: str, pyaudio_stream: Stream, queue: queue.Queue) -> None:
        super().__init__(daemon=True)
        self.buffer = np.array([], dtype="<i2")  # Fixed data type
        self.pyaudio_stream = pyaudio_stream
        self.audio_url = f"http://{esp_ip}:82/audio"
        self.running = False
        self.queue = queue
        self.num_samples = self.SAMPLING_RATE * self.CLASSIFICATION_DURATION

    def stop(self):
        self.running = False

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
                    if self.buffer.size >= self.num_samples:
                        self.queue.put(self.buffer[: self.num_samples])
                        self.buffer = self.buffer[self.num_samples :]

        except requests.RequestException as e:
            print(f"Error occurred: {e}")
        finally:
            self.running = False


if __name__ == "__main__":
    # Start audio reader thread
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16, channels=1, rate=AudioReader.SAMPLING_RATE, output=True
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
