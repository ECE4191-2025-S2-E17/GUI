import threading
import queue
import lightning as pl
from torch.nn.functional import softmax


class AudioClassifier(threading.Thread):
    SAMPLING_RATE = 22050
    CLASSIFICATION_DURATION = 2

    def __init__(
        self,
        input_queue: queue.Queue,
        result_queue: queue.Queue,
        model: pl.LightningModule,
    ) -> None:
        super().__init__(daemon=True)
        self.model = model
        self.running = False
        self.input_queue = input_queue
        self.result_queue = result_queue

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            audio_chunk = self.input_queue.get()
            if audio_chunk is None:
                break
            logits = self.model(audio_chunk)
            confidences = softmax(logits, dim=0)
            self.result_queue.put(confidences)
