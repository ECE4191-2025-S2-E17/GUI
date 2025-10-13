import torch
from torch import nn
import lightning as pl
from lightning.pytorch.utilities.types import OptimizerLRScheduler

from audio.models.pann_model import Transfer_Cnn14

import logging

logger = logging.getLogger(__name__)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

"""
This model expects single-label class indices as targets.
It is trained at 32000 Hz sample rate and 3 second clip length.
"""


class AnimalSoundClassifierModule(pl.LightningModule):

    CLASS_NAMES = sorted(
        [
            "Bat",
            "Cockatoo",
            "Crocodile",
            "Cricket",
            "Dingo",
            "Duck",
            "Frog",
            "FrogmouthTawny",
            "Koala",
            "Kookaburra",
            "Magpie",
            "Platypus",
            "Possum",
            "Snake",
            "Water",
            "Wombat",
            "Noise",
            "Silence",
        ]
    )

    def __init__(
        self,
        pretrained_model_path: str,
        load_original_pann: bool = False,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        freeze_base: bool = True,
    ):
        super().__init__()
        self.save_hyperparameters()

        self.transfer_model = Transfer_Cnn14(
            sample_rate=32000,
            window_size=1024,
            hop_size=320,
            mel_bins=64,
            fmin=50,
            fmax=14000,
            classes_num=len(self.CLASS_NAMES),
            freeze_base=self.hparams.freeze_base,
        )
        if load_original_pann:
            try:
                self.transfer_model.load_from_pretrain(pretrained_model_path)
                logger.info("Loaded original pann model from {}".format(pretrained_model_path))
            except Exception as e:
                logger.error(f"Failed to load original pann model: {e}")
                raise e

        self.criterion = nn.NLLLoss()

    def forward(self, audio: torch.Tensor) -> torch.Tensor:
        """Defines the forward pass."""
        return self.transfer_model(audio)["clipwise_output"]

    def training_step(self, batch, batch_idx):
        waveforms, labels = batch
        if waveforms.dim() == 3 and waveforms.size(1) == 1:
            waveforms = waveforms.squeeze(1)  # Remove channel dimension if present
        logits = self(waveforms)
        loss = self.criterion(logits, labels)

        # Single-label predictions using softmax and argmax
        probs = torch.softmax(logits, dim=1)
        preds = torch.argmax(probs, dim=1)

        # Accuracy
        acc = (preds == labels).float().mean()

        self.log("train_loss", loss, prog_bar=True)
        self.log("train_acc", acc, prog_bar=True)

        return loss

    def validation_step(self, batch, batch_idx):
        waveforms, labels = batch
        if waveforms.dim() == 3 and waveforms.size(1) == 1:
            waveforms = waveforms.squeeze(1)  # Remove channel dimension if present
        logits = self(waveforms)
        loss = self.criterion(logits, labels)

        # Single-label predictions using softmax and argmax
        probs = torch.softmax(logits, dim=1)
        preds = torch.argmax(probs, dim=1)

        # Accuracy
        acc = (preds == labels).float().mean()

        self.log("val_loss", loss, prog_bar=True)
        self.log("val_acc", acc, prog_bar=True)

        return loss

    def test_step(self, batch, batch_idx):
        waveforms, labels = batch
        if waveforms.dim() == 3 and waveforms.size(1) == 1:
            waveforms = waveforms.squeeze(1)  # Remove channel dimension if present
        logits = self(waveforms)
        loss = self.criterion(logits, labels)

        # Single-label predictions using softmax and argmax
        probs = torch.softmax(logits, dim=1)
        preds = torch.argmax(probs, dim=1)

        # Accuracy
        acc = (preds == labels).float().mean()

        self.log("test_loss", loss, prog_bar=False)
        self.log("test_acc", acc, prog_bar=False)

        return loss

    def configure_optimizers(self) -> OptimizerLRScheduler:
        # Access hyperparameters from self.hparams
        optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=self.hparams.learning_rate,
            weight_decay=self.hparams.weight_decay,
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5
        )
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss",
            },
        }

    def get_class_name(self, idx):
        return self.CLASS_NAMES[idx]


if __name__ == "__main__":
    pass
