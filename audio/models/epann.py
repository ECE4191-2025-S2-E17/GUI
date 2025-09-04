"""
Code from: https://github.com/Arshdeep-Singh-Boparai/E-PANNs
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchlibrosa.stft import Spectrogram, LogmelFilterBank
from torchlibrosa.augmentation import SpecAugmentation

CKPT_PATH = "https://github.com/StefanoGiacomelli/epanns_inference/raw/main/epanns_inference/models/checkpoint_closeto_.44.pt"


def init_layer(layer):
    """Initialize a Linear or Convolutional layer."""
    nn.init.xavier_uniform_(layer.weight)

    if hasattr(layer, "bias"):
        if layer.bias is not None:
            layer.bias.data.fill_(0.0)


def do_mixup(x, mixup_lambda):
    out = (
        x[0::2].transpose(0, -1) * mixup_lambda[0::2]
        + x[1::2].transpose(0, -1) * mixup_lambda[1::2]
    )
    return out.transpose(0, -1)


def init_bn(bn):
    """Initialize a Batchnorm layer."""
    bn.bias.data.fill_(0.0)
    bn.weight.data.fill_(1.0)


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels):

        super(ConvBlock, self).__init__()

        self.conv1 = nn.Conv2d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=(3, 3),
            stride=(1, 1),
            padding=(1, 1),
            bias=False,
        )

        self.conv2 = nn.Conv2d(
            in_channels=out_channels,
            out_channels=out_channels,
            kernel_size=(3, 3),
            stride=(1, 1),
            padding=(1, 1),
            bias=False,
        )

        self.bn1 = nn.BatchNorm2d(out_channels)
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.init_weight()

    def init_weight(self):
        init_layer(self.conv1)
        init_layer(self.conv2)
        init_bn(self.bn1)
        init_bn(self.bn2)

    def forward(self, input, pool_size=(2, 2), pool_type="avg"):
        x = input
        x = F.relu_(self.bn1(self.conv1(x)))
        x = F.relu_(self.bn2(self.conv2(x)))
        if pool_type == "max":
            x = F.max_pool2d(x, kernel_size=pool_size)
        elif pool_type == "avg":
            x = F.avg_pool2d(x, kernel_size=pool_size)
        elif pool_type == "avg+max":
            x1 = F.avg_pool2d(x, kernel_size=pool_size)
            x2 = F.max_pool2d(x, kernel_size=pool_size)
            x = x1 + x2
        else:
            raise Exception("Incorrect argument!")

        return x


class ConvBlock_pruned(nn.Module):
    def __init__(self, in_channels_1, out_channels_1, out_channels_2):

        super(ConvBlock_pruned, self).__init__()

        self.conv1 = nn.Conv2d(
            in_channels=in_channels_1,
            out_channels=out_channels_1,
            kernel_size=(3, 3),
            stride=(1, 1),
            padding=(1, 1),
            bias=False,
        )

        self.conv2 = nn.Conv2d(
            in_channels=out_channels_1,
            out_channels=out_channels_2,
            kernel_size=(3, 3),
            stride=(1, 1),
            padding=(1, 1),
            bias=False,
        )

        self.bn1 = nn.BatchNorm2d(out_channels_1)
        self.bn2 = nn.BatchNorm2d(out_channels_2)

        self.init_weight()

    def init_weight(self):
        init_layer(self.conv1)
        init_layer(self.conv2)
        init_bn(self.bn1)
        init_bn(self.bn2)

    def forward(self, input, pool_size=(2, 2), pool_type="avg"):
        x = input
        x = F.relu_(self.bn1(self.conv1(x)))
        x = F.relu_(self.bn2(self.conv2(x)))
        if pool_type == "max":
            x = F.max_pool2d(x, kernel_size=pool_size)
        elif pool_type == "avg":
            x = F.avg_pool2d(x, kernel_size=pool_size)
        elif pool_type == "avg+max":
            x1 = F.avg_pool2d(x, kernel_size=pool_size)
            x2 = F.max_pool2d(x, kernel_size=pool_size)
            x = x1 + x2
        else:
            raise Exception("Incorrect argument!")

        return x


class Cnn14_pruned(nn.Module):
    def __init__(
        self,
        sample_rate=32000,
        window_size=1024,
        hop_size=320,
        mel_bins=64,
        fmin=50,
        fmax=14000,
        classes_num=527,
        p1=0,
        p2=0,
        p3=0,
        p4=0,
        p5=0,
        p6=0,
        p7=0.5,
        p8=0.5,
        p9=0.5,
        p10=0.5,
        p11=0.5,
        p12=0.5,
        pre_trained=True,
    ):
        super(Cnn14_pruned, self).__init__()

        window = "hann"
        center = True
        pad_mode = "constant"
        ref = 1.0
        amin = 1e-10
        top_db = None

        # Spectrogram extractor
        self.spectrogram_extractor = Spectrogram(
            n_fft=window_size,
            hop_length=hop_size,
            win_length=window_size,
            window=window,
            center=center,
            pad_mode=pad_mode,
            freeze_parameters=True,
        )

        # Logmel feature extractor
        self.logmel_extractor = LogmelFilterBank(
            sr=sample_rate,
            n_fft=window_size,
            n_mels=mel_bins,
            fmin=fmin,
            fmax=fmax,
            ref=ref,
            amin=amin,
            top_db=top_db,
            freeze_parameters=True,
        )

        # Spec augmenter
        self.spec_augmenter = SpecAugmentation(
            time_drop_width=64,
            time_stripes_num=2,
            freq_drop_width=8,
            freq_stripes_num=2,
        )

        self.bn0 = nn.BatchNorm2d(64)

        self.conv_block1 = ConvBlock_pruned(
            in_channels_1=1,
            out_channels_1=int(64 * (1 - p1)),
            out_channels_2=int(64 * (1 - p2)),
        )
        self.conv_block2 = ConvBlock_pruned(
            in_channels_1=int(64 * (1 - p2)),
            out_channels_1=int(128 * (1 - p3)),
            out_channels_2=int(128 * (1 - p4)),
        )
        self.conv_block3 = ConvBlock_pruned(
            in_channels_1=int(128 * (1 - p4)),
            out_channels_1=int(256 * (1 - p5)),
            out_channels_2=int(256 * (1 - p6)),
        )
        self.conv_block4 = ConvBlock_pruned(
            in_channels_1=int(256 * (1 - p6)),
            out_channels_1=int(512 * (1 - p7)),
            out_channels_2=int(512 * (1 - p8)),
        )
        self.conv_block5 = ConvBlock_pruned(
            in_channels_1=int(512 * (1 - p8)),
            out_channels_1=int(1024 * (1 - p9)),
            out_channels_2=int(1024 * (1 - p10)),
        )
        self.conv_block6 = ConvBlock_pruned(
            in_channels_1=int(1024 * (1 - p10)),
            out_channels_1=int((1 - p11) * 2048),
            out_channels_2=int(2048 * (1 - p12)),
        )

        self.fc1 = nn.Linear(int(2048 * (1 - p12)), 2048, bias=True)
        self.fc_audioset = nn.Linear(2048, classes_num, bias=True)

        if pre_trained:
            if not os.path.exists("./epann.pt") or not os.path.exists(
                "./models/epann.pt"
            ):
                os.system('wget -O "{}" "{}"'.format("./epann.pt", CKPT_PATH))
            checkpoint = torch.load(
                "./epann.pt" if os.path.exists("./epann.pt") else "./models/epann.pt",
                map_location=lambda storage, loc: storage,
            )
            self.load_state_dict(checkpoint)
        else:
            self.init_weight()

    def init_weight(self):
        init_bn(self.bn0)
        init_layer(self.fc1)
        init_layer(self.fc_audioset)

    def forward(self, input, mixup_lambda=None):
        """Input: (batch_size, data_length)"""
        x = self.spectrogram_extractor(input)  # (batch_size, 1, time_steps, freq_bins)
        x = self.logmel_extractor(x)  # (batch_size, 1, time_steps, mel_bins)

        x = x.transpose(1, 3)
        x = self.bn0(x)
        x = x.transpose(1, 3)

        if self.training:
            x = self.spec_augmenter(x)

        # Mixup on spectrogram
        if self.training and mixup_lambda is not None:
            x = do_mixup(x, mixup_lambda)

        x = self.conv_block1(x, pool_size=(2, 2), pool_type="avg")
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv_block2(x, pool_size=(2, 2), pool_type="avg")
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv_block3(x, pool_size=(2, 2), pool_type="avg")
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv_block4(x, pool_size=(2, 2), pool_type="avg")
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv_block5(x, pool_size=(2, 2), pool_type="avg")
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv_block6(x, pool_size=(1, 1), pool_type="avg")
        x = F.dropout(x, p=0.2, training=self.training)
        x = torch.mean(x, dim=3)

        (x1, _) = torch.max(x, dim=2)
        x2 = torch.mean(x, dim=2)
        x = x1 + x2
        x = F.dropout(x, p=0.5, training=self.training)
        x = F.relu_(self.fc1(x))
        embedding = x.clone()

        x = F.dropout(x, p=0.5, training=self.training)
        clipwise_output = nn.functional.softmax(self.fc_audioset(x))

        output_dict = {"clipwise_output": clipwise_output, "embedding": embedding}

        return output_dict
