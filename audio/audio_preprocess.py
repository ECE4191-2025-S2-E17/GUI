import torch
import torchaudio

"""
Note that this prepares data for model inferencing, NOT playing

"""


def normalize(data: torch.Tensor, mean: float = 0.000011, std: float = 0.002872):
    normalized_data = (data - mean) / std
    return normalized_data


def resample_audio(waveform, current_rate, target_rate):
    if current_rate != target_rate:
        resampler = torchaudio.transforms.Resample(
            orig_freq=current_rate, new_freq=target_rate
        )
        waveform = resampler(waveform)
    return waveform


def convert_to_mono(waveform: torch.Tensor):
    # Check if the waveform has more than one dimension (e.g., (channels, samples))
    if waveform.ndim > 1:
        # If it has a channel dimension and it's greater than 1, take the mean
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0)
        # If it has a single channel, remove the channel dimension
        else:
            waveform = waveform.squeeze(0)
    return waveform


def pad_or_truncate(waveform, target_length):
    if waveform.shape[0] > target_length:
        waveform = waveform[:target_length]
    else:
        padding = target_length - waveform.shape[0]
        waveform = torch.nn.functional.pad(waveform, (0, padding))
    return waveform


def correct_sample(waveform, current_rate, target_rate, target_length=None):
    waveform = resample_audio(waveform, current_rate, target_rate)
    waveform = convert_to_mono(waveform)
    waveform = normalize(waveform)
    if target_length is not None:
        waveform = pad_or_truncate(waveform, target_length)
    return waveform
