import threading
import queue
import numpy as np
import lightning as pl


class AudioReader(threading.Thread):
    SAMPLING_RATE = 22050
    CLASSIFICATION_DURATION = 2

    def __init__(self, queue: queue.Queue, model: pl.LightningModule) -> None:
        self.buffer = np.array([], dtype=">i4")
        self.model = model
        self.audio_url = f"http://{esp_ip}:82/audio"
        self.running = False
        self.queue = queue

    def stop(self):
        self.running = False

    def _run(self):
        self.running = True
        with requests.get(self.audio_url, stream=True, timeout=10) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=4096):
                converted_data_16 = (np.frombuffer(chunk, dtype=">i4") >> 8).astype(
                    "<i2"
                )
                if self.pyaudio_stream.is_active():
                    self.pyaudio_stream.write(converted_data_16.tobytes())
                self.buffer = np.concatenate((self.buffer, converted_data_16))
                if self.buffer.size > self.num_samples:
                    self.queue.put(self.buffer[: self.num_samples])
                self.buffer = self.buffer[self.num_samples :]
