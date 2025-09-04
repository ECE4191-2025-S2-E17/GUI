import torch
from torch import nn
from torchmetrics import F1Score
import lightning as pl
from lightning.pytorch.utilities.types import OptimizerLRScheduler
from torch.nn.utils.rnn import pack_padded_sequence


class AnimalSoundClassifierModule(pl.LightningModule):
    CLASS_NAMES = [
        "Bat",
        "Cockatoo",
        "Crocodile",
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
        "Wombat",
        "Silence",
    ]

    def __init__(
        self,
        embedding_size: int = 2048,
        num_layers: int = 2,
        hidden_size: int = 256,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
    ):
        super().__init__()
        self.save_hyperparameters()

        # embedding of epann feeds into here
        self.lstm = nn.LSTM(
            embedding_size,
            hidden_size,
            batch_first=True,
            num_layers=num_layers,
            bidirectional=False,
        )

        self.classifier_head = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Dropout(p=0.5),
            nn.Linear(hidden_size, len(self.CLASS_NAMES)),
        )
        # self.f1_score = F1Score(
        #     task="multilabel", num_labels=len(self.CLASS_NAMES), average="micro"
        # )
        self.criterion = nn.CrossEntropyLoss()

    def forward(self, embedding_sequence: torch.Tensor, lengths: torch.Tensor):
        """
        embedding_sequence: (batch_size, seq_len, embedding_dim)
        lengths: (batch_size,) number of valid timesteps per sequence
        """
        # Pack padded sequence
        packed_input = pack_padded_sequence(
            embedding_sequence, lengths.cpu(), batch_first=True, enforce_sorted=False
        )

        packed_output, (h_n, c_n) = self.lstm(packed_input)

        # h_n: (num_layers, batch, hidden_dim) → last layer's hidden state
        final_hidden = h_n[-1]  # shape: (batch, hidden_dim)

        # Classifier
        logits = self.classifier_head(final_hidden)
        return logits

    def training_step(self, batch, batch_idx):
        embeddings, lengths, labels = batch
        logits = self(embeddings, lengths)
        loss = self.criterion(logits, labels)

        preds = torch.softmax(logits, dim=-1)
        preds = preds.argmax(dim=-1)
        acc = (preds == labels).float().mean()
        self.log("train_loss", loss, prog_bar=True)
        self.log("train_acc", acc, prog_bar=True)

        return loss

    def validation_step(self, batch, batch_idx):
        embeddings, lengths, labels = batch
        logits = self(embeddings, lengths)
        loss = self.criterion(logits, labels)

        preds = torch.softmax(logits, dim=-1)
        preds = preds.argmax(dim=-1)
        acc = (preds == labels).float().mean()
        self.log("val_loss", loss, prog_bar=True)
        self.log("val_acc", acc, prog_bar=True)

        return loss

    def test_step(self, batch, batch_idx):
        embeddings, lengths, labels = batch
        logits = self(embeddings, lengths)
        loss = self.criterion(logits, labels)

        preds = torch.softmax(logits, dim=-1)
        preds = preds.argmax(dim=-1)
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

    @classmethod
    def get_class_name(cls, idx):
        return cls.CLASS_NAMES[idx]


if __name__ == "__main__":
    pass
