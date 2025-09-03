import threading
import queue
import torch
from torch.nn.functional import softmax
import numpy as np
from collections import deque

from audio.audio_preprocessor import correct_sample
from constants import TARGET_SAMPLING_RATE_HZ, CLIP_SIZE


class AudioClassifier(threading.Thread):
    def __init__(
        self,
        input_queue: queue.Queue,
        result_queue: queue.Queue,
        buffer_size: int = 30,
    ) -> None:
        super().__init__(daemon=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        self.embedding_model = None
        self.classification_model = None
        self.running = False
        self.input_queue = input_queue
        self.result_queue = result_queue
        self.embedding_buffer_size = buffer_size
        self.embedding_buffer = deque()

    def clear_buffer(self):
        self.embedding_buffer.clear()

    def change_buffer_size(self, new_size: int):
        self.embedding_buffer_size = new_size
        while len(self.embedding_buffer) > new_size:
            self.embedding_buffer.popleft()

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            audio_chunk = self.input_queue.get()
            if audio_chunk is None:
                break
            audio_chunk = correct_sample(
                audio_chunk, TARGET_SAMPLING_RATE_HZ, TARGET_SAMPLING_RATE_HZ, CLIP_SIZE
            )
            embeddings = self.embedding_model(audio_chunk.unsqueeze(0).to(self.device))
            if len(self.embedding_buffer) >= self.embedding_buffer_size:
                self.embedding_buffer.popleft()
            self.embedding_buffer.append(embeddings)
            logits = self.classification_model(
                torch.vstack(self.embedding_buffer).to(self.device)
            )
            confidences = softmax(logits, dim=0)
            self.result_queue.put(confidences)
