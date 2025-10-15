from ctypes import cast
import threading
import queue
import torch
from audio.models.cnn_single_label_model import AnimalSoundClassifierModule
from collections import deque
from audio.constants import TARGET_SAMPLING_RATE_HZ, CLIP_SIZE
from audio.audio_preprocess import correct_sample
import noisereduce as nr


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
        self.classifying = True

    def pause(self):
        self.classifying = False

    def resume(self):
        self.classifying = True

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            queue_item = self.input_queue.get()

            # Handle both old format (just audio_chunk) and new format (audio_chunk, timestamp)
            if isinstance(queue_item, tuple):
                audio_chunk, timestamp = queue_item
            else:
                audio_chunk = queue_item
                timestamp = None

            if not self.classifying:
                continue
            # convert audio_chunk to float
            audio_chunk = audio_chunk / 32768.0
            if audio_chunk is None:
                break
            audio_chunk = nr.reduce_noise(
                y=audio_chunk,
                sr=TARGET_SAMPLING_RATE_HZ,
                stationary=True,
                prop_decrease=0.7,
                n_fft=512,
                n_std_thresh_stationary=1.3,
                chunk_size=CLIP_SIZE,
            )
            audio_chunk = torch.Tensor(audio_chunk).unsqueeze(0).to(self.device)
            audio_chunk = correct_sample(
                audio_chunk, TARGET_SAMPLING_RATE_HZ, TARGET_SAMPLING_RATE_HZ, CLIP_SIZE
            )  # shape (96000,)
            with torch.no_grad():
                audio_chunk = audio_chunk.unsqueeze(0)  # shape (1, 96000)
                # logits are alreaady softmaxed in the model
                logits = self.classification_model(
                    audio_chunk,
                )
            # Pass timestamp along with logits
            self.result_queue.put((logits, timestamp))

    def init_models(self):
        self.classification_model = AnimalSoundClassifierModule(
            load_original_pann=False,
            freeze_base=True,
            pretrained_model_path="",
        )
        self.classification_model.load_state_dict(
            torch.load(
                "audio/models/single_label_classifier.pth", map_location=self.device
            )
        )
        self.classification_model.to(self.device)
        self.classification_model.eval()

    def get_result(
        self,
        confidences: torch.Tensor,
        threshold: float = 0.5,
        timestamp: float | None = None,
    ) -> dict:
        confidences = torch.exp(confidences.squeeze(0)).cpu()
        pred = int(torch.argmax(confidences).item())
        cls_name = self.classification_model.get_class_name(pred)

        result = {
            "name": cls_name if confidences[pred].item() >= threshold else "Nothing",
            "confidence": (
                confidences[pred].item()
                if confidences[pred].item() >= threshold
                else 1 - confidences[pred].item()
            ),
        }

        # Add timestamp if provided
        if timestamp is not None:
            result["timestamp"] = timestamp

        return result
