"""Datasets over the cached ASVspoof 2019 LA features.

``ASVspoofTrainDataset`` yields window 0 of each utterance (the first 4 s,
repeated if short), the training input. ``ASVspoofWindowDataset`` yields every
window, so evaluation can average the logits of all windows of an utterance.
Both return ``(feature tensor (1, bands, 401) float32, label, utt_id)`` with
label 1 = spoof, 0 = bona fide.

The cache is a float16 memory map, opened lazily in each process so that
DataLoader workers never pickle the array.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset


class CachedSplit:
    """Read-only view of one front end's features for one split."""

    def __init__(self, features_dir: str | Path, frontend: str, split: str) -> None:
        self.dir = Path(features_dir) / frontend
        self.frontend = frontend
        self.split = split
        progress_path = self.dir / f"{split}.progress.json"
        if not progress_path.exists():
            raise FileNotFoundError(f"No feature cache for {frontend}/{split} in {self.dir}")
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if not progress.get("complete"):
            raise RuntimeError(
                f"Feature cache {frontend}/{split} is incomplete "
                f"({progress.get('done')}/{progress.get('utterances')}); finish extraction first."
            )
        self.manifest_sha256 = progress.get("manifest_sha256")
        with open(self.dir / f"{split}_index.csv", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.utt_ids = [r["utt_id"] for r in rows]
        self.labels = np.array([int(r["label"]) for r in rows], dtype=np.int64)
        self.attack_ids = [r["attack_id"] for r in rows]
        self.row_start = np.array([int(r["row_start"]) for r in rows], dtype=np.int64)
        self.n_windows = np.array([int(r["n_windows"]) for r in rows], dtype=np.int64)
        self._array: np.ndarray | None = None

    @property
    def array(self) -> np.ndarray:
        if self._array is None:
            self._array = np.load(self.dir / f"{self.split}.npy", mmap_mode="r")
        return self._array

    def __getstate__(self) -> dict:
        state = self.__dict__.copy()
        state["_array"] = None  # reopen in the worker instead of pickling
        return state

    def __len__(self) -> int:
        return len(self.utt_ids)


class ASVspoofTrainDataset(Dataset):
    """Window 0 of each utterance, optionally restricted to a subset of indices."""

    def __init__(self, cache: CachedSplit, indices: np.ndarray | None = None) -> None:
        self.cache = cache
        self.indices = np.arange(len(cache)) if indices is None else np.asarray(indices)

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, item: int):
        index = int(self.indices[item])
        row = int(self.cache.row_start[index])
        features = torch.from_numpy(np.asarray(self.cache.array[row], dtype=np.float32)).unsqueeze(0)
        return features, int(self.cache.labels[index]), self.cache.utt_ids[index]

    @property
    def labels(self) -> np.ndarray:
        return self.cache.labels[self.indices]


class ASVspoofWindowDataset(Dataset):
    """Every window of every utterance, for window-averaged scoring."""

    def __init__(self, cache: CachedSplit, indices: np.ndarray | None = None) -> None:
        self.cache = cache
        utterances = np.arange(len(cache)) if indices is None else np.asarray(indices)
        self.window_rows = np.concatenate(
            [np.arange(cache.row_start[u], cache.row_start[u] + cache.n_windows[u]) for u in utterances]
        )
        self.window_utt = np.repeat(utterances, cache.n_windows[utterances])

    def __len__(self) -> int:
        return len(self.window_rows)

    def __getitem__(self, item: int):
        row = int(self.window_rows[item])
        index = int(self.window_utt[item])
        features = torch.from_numpy(np.asarray(self.cache.array[row], dtype=np.float32)).unsqueeze(0)
        return features, int(self.cache.labels[index]), self.cache.utt_ids[index]


def average_by_utterance(utt_ids: list[str], values: np.ndarray) -> dict[str, float]:
    """Mean of per-window values for each utterance id."""
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for utt, value in zip(utt_ids, np.asarray(values, dtype=np.float64).ravel(), strict=True):
        sums[utt] = sums.get(utt, 0.0) + float(value)
        counts[utt] = counts.get(utt, 0) + 1
    return {utt: sums[utt] / counts[utt] for utt in sums}
