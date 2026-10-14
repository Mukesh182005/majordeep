"""Provenance record for every results folder written for the paper.

Each ``paper_results/<experiment>/config.json`` embeds the dict returned by
:func:`collect_provenance`, so any number in the paper can be traced to the
exact code, data manifest, environment and command that produced it
(CLAUDE.md, research-integrity rule 6).
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Libraries whose version can change a score. Read from package metadata so
# that recording them never imports (or fails on) a heavy package.
TRACKED_LIBRARIES = (
    "numpy",
    "scipy",
    "scikit-learn",
    "torch",
    "torchvision",
    "torchaudio",
    "transformers",
    "timm",
    "librosa",
    "soundfile",
    "Pillow",
    "opencv-python-headless",
)


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Hex sha256 of a file, read in chunks so large manifests are fine."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()


def git_state() -> dict:
    """Current commit and whether the working tree has uncommitted changes.

    A dirty tree means the commit alone does not reproduce the run, so the
    flag is recorded rather than silently ignored.
    """
    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    return {
        "git_commit": commit,
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": None if status is None else bool(status),
    }


def library_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in TRACKED_LIBRARIES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def torch_environment() -> dict:
    """Torch, CUDA and GPU details; every field is None when torch is absent."""
    info = {"torch": None, "cuda_build": None, "cuda_available": False, "gpu_name": None}
    try:
        import torch
    except ImportError:
        return info
    info["torch"] = torch.__version__
    info["cuda_build"] = torch.version.cuda
    info["cuda_available"] = bool(torch.cuda.is_available())
    if info["cuda_available"]:
        info["gpu_name"] = torch.cuda.get_device_name(0)
    return info


def collect_provenance(
    manifest_path: Path | str | None = None,
    seeds: list[int] | int | None = None,
    argv: list[str] | None = None,
) -> dict:
    """Everything needed to say where a result came from.

    ``manifest_path`` is hashed so that a later change to the data list is
    detectable; ``argv`` defaults to the running process's command line.
    """
    manifest_sha256 = None
    manifest_rel = None
    if manifest_path is not None:
        manifest = Path(manifest_path)
        manifest_sha256 = sha256_file(manifest)
        try:
            manifest_rel = manifest.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            # Outside the repository: record only the name, never a local
            # absolute path (CLAUDE.md, data rules).
            manifest_rel = manifest.name

    if isinstance(seeds, int):
        seeds = [seeds]

    return {
        **git_state(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        **torch_environment(),
        "libraries": library_versions(),
        "utc_time": datetime.now(UTC).isoformat(timespec="seconds"),
        "command_line": list(sys.argv if argv is None else argv),
        "manifest": manifest_rel,
        "manifest_sha256": manifest_sha256,
        "seeds": seeds,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(collect_provenance(sys.argv[1] if len(sys.argv) > 1 else None), indent=2))
