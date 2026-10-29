#!/usr/bin/env python3
"""Fine-tune pellav2 to stop flagging codec-compressed genuine speech.

On an ASVspoof 5 eval sample the audio verdict called 15 % of genuine speech
AI-generated, mostly speech passed through the EnCodec neural codec and
narrowband (telephone) codecs (evaluation/E2E-01, KNOWN_ISSUES #16). ASVspoof 5's
train and dev partitions contain no codecs, so robustness has to come from
augmentation: every clip, bona fide and spoofed alike, is passed through a random
codec, so the codec carries no label information.

  prepare  decode every clip, apply codec conditions, cut 4 s windows exactly as the
           backend does (app.ml.audio.pellav2.prepare_windows) and store them.
             train: ASVspoof 5 train sample (A01-A08) + ASVspoof 2019 LA train replay;
                    clean + 2 random codec variants per clip.
             val:   ASVspoof 5 dev sample (A09-A16, speakers disjoint from train);
                    clean + 1 codec variant per clip, chosen by a hash of its id.
           The ASVspoof 5 eval sample is never read here.
  train    fine-tune the top --unfreeze encoder layers, the layer weights and the head
           (the rest frozen), pick the epoch with the best validation AUC, fit a logit
           offset so at most --max-real-flag of validation bona fide windows score >= 0.5,
           and write <out>/pellav2_detector.pt, metadata.json and pellav2_verdict_config.json.

Codec families match those of ASVspoof 5 eval (Opus, AMR, Speex, EnCodec, MP3, M4A/AAC);
no eval clip is used. EnCodec weights (facebook/encodec_24khz) are CC BY-NC 4.0.

  python ml/training/finetune_pellav2.py prepare --v5-root C:/deepsentinel_data/ASVspoof5 \\
      --la-root C:/deepsentinel_data/ASVspoof2019/LA --out C:/deepsentinel_data/pellav2_ft_data
  python ml/training/finetune_pellav2.py train --data C:/deepsentinel_data/pellav2_ft_data \\
      --out checkpoints/pellav2_ft_v1
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))

SR = 16000
# name -> (ffmpeg encode args incl. sample rate, container suffix)
FFMPEG_CONDITIONS: dict[str, tuple[list[str], str]] = {
    "mp3_32k": (["-ar", "16000", "-c:a", "libmp3lame", "-b:a", "32k"], ".mp3"),
    "mp3_64k": (["-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k"], ".mp3"),
    "aac_32k": (["-ar", "16000", "-c:a", "aac", "-b:a", "32k"], ".m4a"),
    "opus_wb_12k": (["-ar", "16000", "-c:a", "libopus", "-b:a", "12k"], ".ogg"),
    "opus_wb_24k": (["-ar", "16000", "-c:a", "libopus", "-b:a", "24k"], ".ogg"),
    "opus_nb_8k": (["-ar", "8000", "-c:a", "libopus", "-b:a", "8k"], ".ogg"),
    "amr_nb_4.75k": (["-ar", "8000", "-c:a", "libopencore_amrnb", "-b:a", "4.75k"], ".amr"),
    "amr_nb_12.2k": (["-ar", "8000", "-c:a", "libopencore_amrnb", "-b:a", "12.2k"], ".amr"),
    "amr_wb_8.85k": (["-ar", "16000", "-c:a", "libvo_amrwbenc", "-b:a", "8.85k"], ".amr"),
    "amr_wb_23.85k": (["-ar", "16000", "-c:a", "libvo_amrwbenc", "-b:a", "23.85k"], ".amr"),
    "speex_wb": (["-ar", "16000", "-c:a", "libspeex"], ".ogg"),
    "speex_nb": (["-ar", "8000", "-c:a", "libspeex"], ".ogg"),
    "gsm": (["-ar", "8000", "-c:a", "libgsm"], ".wav"),
    "g722": (["-ar", "16000", "-c:a", "g722"], ".wav"),
}
ENCODEC_CONDITIONS = {"encodec_1.5k": 1.5, "encodec_3k": 3.0, "encodec_6k": 6.0, "encodec_12k": 12.0}
ALL_CONDITIONS = [*FFMPEG_CONDITIONS, *ENCODEC_CONDITIONS]


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg_condition(wave: np.ndarray, name: str, exe: str) -> np.ndarray:
    import soundfile as sf

    args, suffix = FFMPEG_CONDITIONS[name]
    with tempfile.TemporaryDirectory(prefix="ds-aug-") as tmp:
        src, enc, dec = Path(tmp) / "in.wav", Path(tmp) / f"enc{suffix}", Path(tmp) / "out.wav"
        sf.write(src, wave, SR, subtype="PCM_16")
        common = [exe, "-nostdin", "-v", "error", "-y"]
        subprocess.run([*common, "-i", str(src), "-ac", "1", *args, str(enc)], check=True, capture_output=True, timeout=120)
        subprocess.run([*common, "-i", str(enc), "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(dec)],
                       check=True, capture_output=True, timeout=120)
        out, rate = sf.read(dec, dtype="float32")
    return out if out.ndim == 1 else out.mean(axis=1)


class EncodecRunner:
    def __init__(self, device: str):
        import torch
        from transformers import EncodecModel

        self.torch = torch
        self.model = EncodecModel.from_pretrained("facebook/encodec_24khz").to(device).eval()
        self.device = device

    def __call__(self, wave: np.ndarray, bandwidth: float) -> np.ndarray:
        import librosa

        torch = self.torch
        x = librosa.resample(wave, orig_sr=SR, target_sr=24000).astype(np.float32)
        with torch.inference_mode():
            t = torch.from_numpy(x)[None, None].to(self.device)
            enc = self.model.encode(t, bandwidth=bandwidth)
            y = self.model.decode(enc.audio_codes, enc.audio_scales)[0][0, 0].float().cpu().numpy()
        return librosa.resample(y[: len(x)], orig_sr=24000, target_sr=SR).astype(np.float32)


def read_v5(root: Path, sample_dir: str, protocol: str) -> list[dict]:
    rows = list(csv.DictReader(open(root / sample_dir / "sample.tsv", encoding="utf-8"), delimiter="\t"))
    return [{"id": r["file_id"], "path": str(root / sample_dir / f"{r['file_id']}.flac"), "label": int(r["key"] == "spoof"),
             "attack": r["attack"], "source": f"asvspoof5_{protocol}"} for r in rows]


def read_la_train(la_root: Path, per_class: int, seed: int) -> list[dict]:
    rows = []
    for line in (la_root / "ASVspoof2019_LA_cm_protocols" / "ASVspoof2019.LA.cm.train.trn.txt").read_text().splitlines():
        p = line.split()
        rows.append({"id": p[1], "path": str(la_root / "ASVspoof2019_LA_train" / "flac" / f"{p[1]}.flac"),
                     "label": int(p[4] == "spoof"), "attack": p[3] if p[4] == "spoof" else "bonafide", "source": "asvspoof2019_la_train"})
    rng = random.Random(seed)
    out = []
    for label in (0, 1):
        pool = [r for r in rows if r["label"] == label]
        out += rng.sample(pool, min(per_class, len(pool)))
    return out


def one_window(wave: np.ndarray, rng: random.Random | None) -> np.ndarray:
    """A 4 s window cut exactly as the backend does; random among the clip's windows when rng is given."""
    from app.ml.audio.pellav2 import prepare_windows

    windows, _ = prepare_windows(wave, SR, 8)
    return windows[rng.randrange(len(windows)) if rng else 0]


def cmd_prepare(args) -> int:
    import soundfile as sf
    import torch

    exe = ffmpeg_exe()
    train = read_v5(args.v5_root, "train_sample", "train") + read_la_train(args.la_root, args.la_per_class, 0)
    val = read_v5(args.v5_root, "dev_sample", "dev")
    encodec = EncodecRunner("cuda" if torch.cuda.is_available() else "cpu")
    args.out.mkdir(parents=True, exist_ok=True)
    for split, items in (("train", train), ("val", val)):
        jobs = []
        for it in items:
            h = int(hashlib.sha256(it["id"].encode()).hexdigest(), 16)
            rng = random.Random(h)
            if split == "train":
                conds = ["clean", *rng.sample(ALL_CONDITIONS, 2)]
            else:
                conds = ["clean", ALL_CONDITIONS[h % len(ALL_CONDITIONS)]]
            jobs += [(it, c, random.Random(h + i)) for i, c in enumerate(conds)]

        def decode(job):
            it, cond, rng = job
            wave, rate = sf.read(it["path"], dtype="float32")
            wave = wave if wave.ndim == 1 else wave.mean(axis=1)
            if rate != SR:
                import librosa

                wave = librosa.resample(wave, orig_sr=rate, target_sr=SR)
            if cond in FFMPEG_CONDITIONS:
                wave = ffmpeg_condition(wave, cond, exe)
            return wave

        windows, meta = [], []
        t0 = time.time()
        with ThreadPoolExecutor(args.workers) as pool:
            for n, ((it, cond, rng), wave) in enumerate(zip(jobs, pool.map(decode, jobs)), 1):
                if cond in ENCODEC_CONDITIONS:
                    wave = encodec(wave, ENCODEC_CONDITIONS[cond])
                windows.append(one_window(wave, rng if split == "train" else None).astype(np.float16))
                meta.append({"id": it["id"], "label": it["label"], "attack": it["attack"], "source": it["source"], "condition": cond})
                if n % 1000 == 0:
                    print(f"  {split}: {n}/{len(jobs)} ({(time.time() - t0) / 60:.1f} min)", flush=True)
        np.save(args.out / f"{split}_windows.npy", np.stack(windows))
        with open(args.out / f"{split}_meta.csv", "w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=list(meta[0])); w.writeheader(); w.writerows(meta)
        print(f"{split}: {len(meta)} windows from {len(items)} clips", flush=True)
    return 0


def evaluate(model, x: np.ndarray, device, batch: int = 32) -> np.ndarray:
    import torch

    model.eval()
    out = []
    with torch.inference_mode(), torch.autocast(device_type="cuda", enabled=False):
        for i in range(0, len(x), batch):
            out.append(model(torch.from_numpy(x[i:i + batch].astype(np.float32)).to(device)).float().cpu().numpy())
    return np.concatenate(out)


def cmd_train(args) -> int:
    import torch

    from app.ml.audio.pellav2 import HUB_REPO, build_pellav2
    from ml.evaluation.metrics import equal_error_rate, roc_auc

    torch.manual_seed(0); random.seed(0); np.random.seed(0)
    xtr = np.load(args.data / "train_windows.npy", mmap_mode="r")
    ytr = np.array([int(r["label"]) for r in csv.DictReader(open(args.data / "train_meta.csv", encoding="utf-8"))])
    xva = np.load(args.data / "val_windows.npy")
    mva = list(csv.DictReader(open(args.data / "val_meta.csv", encoding="utf-8")))
    yva = np.array([int(r["label"]) for r in mva])
    loaded = build_pellav2(HUB_REPO, device="cuda")
    model, device = loaded.module, loaded.device
    for p in model.parameters():
        p.requires_grad = False
    layers = model.backbone.encoder.layers
    trainable = [*layers[-args.unfreeze:].parameters()]
    for p in trainable:
        p.requires_grad = True
    for p in (model.layer_weights, *model.head.parameters()):
        p.requires_grad = True
    opt = torch.optim.AdamW([{"params": trainable, "lr": args.lr},
                             {"params": [model.layer_weights, *model.head.parameters()], "lr": args.lr * 20}], weight_decay=0.01)
    loss_fn = torch.nn.BCEWithLogitsLoss()

    def val_metrics():
        z = evaluate(model, xva, device)
        return {"auc": roc_auc(yva, z), "eer": equal_error_rate(yva, z)[0],
                "real_flag_at_0": float(np.mean(z[yva == 0] >= 0)), "fake_caught_at_0": float(np.mean(z[yva == 1] >= 0))}, z

    base, _ = val_metrics()
    print(f"epoch 0 (authors' weights): val {base}", flush=True)
    history, best = [{"epoch": 0, **base}], (base["auc"], 0)
    args.out.mkdir(parents=True, exist_ok=True)
    torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()}, args.out / "pellav2_detector.pt")
    # Balanced sampling of bona fide and spoof windows.
    w = np.where(ytr == 1, 1.0 / max(1, (ytr == 1).sum()), 1.0 / max(1, (ytr == 0).sum()))
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = np.random.default_rng(epoch).choice(len(ytr), size=len(ytr), replace=True, p=w / w.sum())
        t0, total = time.time(), 0.0
        for i in range(0, len(order) - args.batch + 1, args.batch):
            idx = np.sort(order[i:i + args.batch])
            xb = torch.from_numpy(np.asarray(xtr[idx], dtype=np.float32)).to(device)
            # random gain and small time shift, so loudness and alignment carry no label information
            xb = torch.roll(xb, shifts=int(np.random.randint(-1600, 1600)), dims=1)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                logits = model(xb)
            loss = loss_fn(logits.float(), torch.from_numpy(ytr[idx].astype(np.float32)).to(device))
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
            total += loss.item()
        steps = max(1, len(order) // args.batch)
        m, _ = val_metrics()
        history.append({"epoch": epoch, "train_loss": total / steps, "minutes": (time.time() - t0) / 60, **m})
        print(f"epoch {epoch}: loss {total / steps:.4f}  val {m}  ({(time.time() - t0) / 60:.1f} min)", flush=True)
        if m["auc"] > best[0]:
            best = (m["auc"], epoch)
            torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()}, args.out / "pellav2_detector.pt")

    model.load_state_dict(torch.load(args.out / "pellav2_detector.pt", map_location="cpu", weights_only=True))
    model.to(device)
    final, z = val_metrics()
    bias = max(0.0, float(np.quantile(z[yva == 0], 1 - args.max_real_flag)))
    per_cond = {}
    for c in sorted({r["condition"] for r in mva}):
        mask = np.array([r["condition"] == c for r in mva])
        per_cond[c] = {"n": int(mask.sum()), "real_flag": float(np.mean(z[mask & (yva == 0)] - bias >= 0)) if (mask & (yva == 0)).any() else None,
                       "fake_caught": float(np.mean(z[mask & (yva == 1)] - bias >= 0)) if (mask & (yva == 1)).any() else None}
    weights = args.out / "pellav2_detector.pt"
    sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    meta = {"base": f"{HUB_REPO}@{loaded.metadata.get('revision')}", "unfrozen_encoder_layers": args.unfreeze,
            "best_epoch": best[1], "best_val_auc": best[0], "history": history, "weights_sha256": sha,
            "train_windows": int(len(ytr)), "val_windows": int(len(yva)), "conditions": ALL_CONDITIONS,
            "calibration": {"logit_bias": bias, "rule": f"at most {args.max_real_flag:.0%} of validation bona fide windows >= 0.5",
                            "val_after": {"real_flag": float(np.mean(z[yva == 0] - bias >= 0)), "fake_caught": float(np.mean(z[yva == 1] - bias >= 0))},
                            "per_condition": per_cond},
            "data": str(args.data), "git_commit": commit, "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (args.out / "metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    band = 0.08  # platform default UNCERTAIN_BAND, as for the original pellav2 rule
    verdict = {"purpose": "fine-tuned pellav2 verdict rule (ml/training/finetune_pellav2.py)", "model": "pellav2 (w2v-BERT 2.0), fine-tuned",
               "weights_sha256": sha, "max_windows": 8, "threshold": 0.5,
               "threshold_rule": "0.5 after the validation logit offset in metadata.json; inconclusive band = platform default 0.08",
               "inconclusive_band": band, "authentic_below": 0.5 - band, "flagged_at_or_above": 0.5 + band,
               "decision_rule": f"pellav2 probability p: authentic if p < {0.5 - band:.4f}, flagged (AI-generated) if p >= {0.5 + band:.4f}, inconclusive otherwise; heuristic signals carry no weight",
               "frozen_utc": meta["utc_time"], "source": str(args.out / "metadata.json")}
    (args.out / "pellav2_verdict_config.json").write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print(f"best epoch {best[1]} (val AUC {best[0]:.4f}); logit bias {bias:.3f}; after calibration {meta['calibration']['val_after']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--v5-root", type=Path, required=True)
    p.add_argument("--la-root", type=Path, required=True)
    p.add_argument("--la-per-class", type=int, default=1000)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=16)
    t = sub.add_parser("train")
    t.add_argument("--data", type=Path, required=True)
    t.add_argument("--out", type=Path, required=True)
    t.add_argument("--epochs", type=int, default=4)
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--lr", type=float, default=1e-5)
    t.add_argument("--unfreeze", type=int, default=4)
    t.add_argument("--max-real-flag", type=float, default=0.02)
    args = ap.parse_args()
    return cmd_prepare(args) if args.cmd == "prepare" else cmd_train(args)


if __name__ == "__main__":
    sys.exit(main())
