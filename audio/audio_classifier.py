import threading
import queue
import torch
from torch.nn.functional import softmax
from audio.models.epann import Cnn14_pruned as Epann
from audio.models.temporal_classifier_model import AnimalSoundClassifierModule
from collections import deque
from audio.constants import TARGET_SAMPLING_RATE_HZ, CLIP_SIZE
from audio.audio_preprocessor import correct_sample


class AudioClassifier(threading.Thread):
    def __init__(
        self,
        input_queue: queue.Queue,
        result_queue: queue.Queue,
        buffer_size: int = 14,
    ) -> None:
        super().__init__(daemon=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        self.init_models()
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
            # convert audio_chunk to float
            audio_chunk = audio_chunk / 32768.0
            if audio_chunk is None:
                break
            audio_chunk = correct_sample(
                audio_chunk, TARGET_SAMPLING_RATE_HZ, TARGET_SAMPLING_RATE_HZ, CLIP_SIZE
            )
            with torch.no_grad():
                embeddings = self.embedding_model(
                    audio_chunk.unsqueeze(0).to(self.device)
                )["embedding"]
                self.embedding_buffer.append(embeddings)
                if len(self.embedding_buffer) >= self.embedding_buffer_size:
                    self.embedding_buffer.popleft()
                else:
                    continue
                logits = self.classification_model(
                    torch.vstack(list(self.embedding_buffer))
                    .unsqueeze(0)
                    .to(self.device),
                    torch.Tensor([len(self.embedding_buffer)]),
                )
                confidences = softmax(logits, dim=1)
            self.result_queue.put(confidences)

    def init_models(self):
        self.classification_model = AnimalSoundClassifierModule.load_from_checkpoint(
            checkpoint_path="./audio/models/final_model_rnn.ckpt"
        )
        self.classification_model.to(self.device)
        self.classification_model.eval()
        self.embedding_model = Epann(
            pre_trained=True, sample_rate=TARGET_SAMPLING_RATE_HZ
        ).to(self.device)
        self.embedding_model.eval()

    def get_result(self, confidences: torch.Tensor):
        confidences = confidences.squeeze(0).cpu()
        pred = confidences.argmax().item()
        cls_name = self.classification_model.CLASS_NAMES[pred]
        return {"name": cls_name, "confidence": confidences[pred].item()}
