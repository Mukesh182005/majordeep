"""Torch datasets backed by the manifests the preprocessing scripts write."""

from __future__ import annotations

import random
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image
import torchvision.transforms as T

from ml.common import read_manifest


class FaceCropDataset(Dataset):
    """Face crops for the image/video detector, with fast C-accelerated transforms."""

    def __init__(
        self, manifest: str | Path, split: str, size: int = 224, augment: bool | None = None
    ) -> None:
        raw_rows = read_manifest(Path(manifest), split)
        if not raw_rows:
            raise ValueError(f"Manifest {manifest} has no rows for split '{split}'")

        self.paths = [r["path"] for r in raw_rows]
        self.labels_arr = np.array([float(r["label"]) for r in raw_rows], dtype=np.float32)
        del raw_rows

        self.size = size
        self.augment = (split == "train") if augment is None else augment

        if self.augment:
            self.transform = T.Compose([
                T.Resize((size, size)),
                T.RandomHorizontalFlip(),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        else:
            self.transform = T.Compose([
                T.Resize((size, size)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        path = self.paths[index]
        with Image.open(path) as opened:
            img = opened.convert("RGB")
        tensor = self.transform(img)
        return tensor, torch.tensor([self.labels_arr[index]], dtype=torch.float32)

    @property
    def labels(self) -> list[int]:
        return [int(lbl) for lbl in self.labels_arr]


class AudioWindowDataset(Dataset):
    """Log-Mel spectrograms of pre-windowed audio for the LCNN."""

    def __init__(
        self,
        manifest: str | Path,
        split: str,
        target_frames: int = 400,
        n_mels: int = 80,
    ) -> None:
        self.rows = read_manifest(Path(manifest), split)
        self.target_frames = target_frames
        self.n_mels = n_mels
        if not self.rows:
            raise ValueError(f"Manifest {manifest} has no rows for split '{split}'")

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        import numpy as np
        from app.ml.preprocessing import log_mel_spectrogram

        row = self.rows[index]
        samples = np.load(row["path"])
        mel = log_mel_spectrogram(samples, n_mels=self.n_mels)

        if mel.shape[1] > self.target_frames:
            mel = mel[:, :self.target_frames]
        elif mel.shape[1] < self.target_frames:
            mel = np.pad(mel, ((0, 0), (0, self.target_frames - mel.shape[1])))

        tensor = torch.from_numpy(mel).unsqueeze(0)
        return tensor, torch.tensor([float(row["label"])])

    @property
    def labels(self) -> list[int]:
        return [row["label"] for row in self.rows]
