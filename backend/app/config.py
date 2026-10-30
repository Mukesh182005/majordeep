"""Application settings, loaded from environment variables / .env."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Repository root: backend/app/config.py -> backend/app -> backend -> <root>
ROOT_DIR = Path(__file__).resolve().parents[2]

# The placeholder shipped in .env.example. Booting production with it would sign
# every token with a value published in this repository.
INSECURE_JWT_SECRET = "change-me-in-production"
MIN_JWT_SECRET_LENGTH = 32

MEDIA_TYPES = ("image", "audio", "video")

# A list setting read from the environment as "a,b,c" or as a JSON list. Without
# NoDecode, pydantic-settings accepts only JSON, so the comma form documented in
# .env.example (and docker-compose's CORS_ORIGINS default) failed at startup.
CsvList = Annotated[list[str], NoDecode]


class InsecureConfigurationError(RuntimeError):
    """Raised when a production deployment is configured unsafely."""


class Settings(BaseSettings):
    """All runtime configuration. See .env.example for documentation."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- API ---
    app_name: str = "Deepfake Detection Platform"
    api_v1_prefix: str = "/api"
    environment: str = "development"
    debug: bool = True

    # --- Security ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # --- Database ---
    # Anchored to the repository root, not the working directory, so the dev
    # server works whether it is started from the repo root or from backend/.
    database_url: str = f"sqlite:///{ROOT_DIR / 'storage' / 'deepfake.db'}"

    # --- Queue ---
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # --- Storage ---
    storage_dir: Path = ROOT_DIR / "storage" / "uploads"
    evidence_dir: Path = ROOT_DIR / "storage" / "evidence"
    report_dir: Path = ROOT_DIR / "storage" / "reports"
    max_upload_mb: int = 100

    # --- Rate limiting ---
    upload_rate_limit_per_hour: int = 500
    guest_rate_limit_per_hour: int = 500
    # Reverse proxies (IP addresses or CIDR networks) whose X-Real-IP header is
    # believed. Requests from anywhere else are counted by their own address:
    # X-Forwarded-For and X-Real-IP from a client are never trusted.
    trusted_proxies: CsvList = Field(default_factory=list)

    # --- Public-upload limits and retention ---
    enabled_media_types: CsvList = Field(default_factory=lambda: list(MEDIA_TYPES))
    max_audio_seconds: float = 600.0
    max_video_seconds: float = 300.0
    # Guest jobs (no account) and their files are deleted after this many hours.
    retention_hours: int = 72

    # --- Login cookie and signed links ---
    auth_cookie_name: str = "deepsentinel_session"
    # None: Secure in production only, so plain-http local development works.
    auth_cookie_secure: bool | None = None
    signed_url_ttl_seconds: int = 300

    # --- Models ---
    checkpoint_dir: Path = ROOT_DIR / "checkpoints"
    image_model_backbone: str = "efficientnet_b4"
    image_model_version: str = "image-detector-v1.0.0"
    audio_model_version: str = "audio-lcnn-v1.0.0"
    video_model_version: str = "video-frame-agg-v1.0.0"
    video_sample_fps: float = 1.0
    video_max_frames: int = 32
    audio_sample_rate: int = 16000
    audio_window_seconds: float = 4.0
    device: str = "cpu"
    # The face-crop checkpoint was trained on StyleGAN faces only. On real vs
    # modern-AI photos with faces it flagged 21% of real faces and 15% of AI
    # faces, so its score is reported but kept out of verdicts until a
    # retrained model is validated.
    face_model_in_verdict: bool = False
    # GenD face-swap detector (app/ml/gend.py; pretrained by its authors, WACV 2026, MIT).
    gend_enabled: bool = True
    gend_model_id: str = "yermandy/GenD_CLIP_L_14"
    # On after measurement (evaluation/VIDEO-GEND-01, 80 held-out DFD videos): face swaps called
    # MANIPULATED 2.5 % -> 72.5 %, real videos 0 -> 1 of 40. Accepted by the project owner on
    # 2026-10-29 although it exceeds the pre-set +2-point limit by one video.
    gend_in_verdict: bool = True
    video_scene_frames: int = 8  # frames scored by the scene AI detectors per video (was 1)
    # Audio model stage. "lcnn_asvspoof" (default): the ASVspoof 2019 LA-trained
    # LCNN chosen on dev, with the dev-fitted calibration and checkpoint hash in
    # audio_lcnn_calibration_file and the verdict rule frozen on dev in
    # audio_verdict_config_file; its probability alone decides the audio verdict.
    # "legacy": hand-set rules only, no trained model (results are marked
    # experimental); kept so the previous behaviour can be restored.
    audio_model_source: str = "lcnn_asvspoof"
    audio_lcnn_calibration_file: Path = ROOT_DIR / "paper" / "config" / "audio_calibration.json"
    audio_verdict_config_file: Path = ROOT_DIR / "paper" / "config" / "frozen_audio_config.json"
    # Codec families (mp3, aac, opus; resample = audio not at 16 kHz) on which the served audio model flagged
    # more than 5% of bona fide dev speech (paper/config/audio_codec_plan.json,
    # guard_rule). Audio in these codecs gets an INCONCLUSIVE audio verdict, and
    # a video's audio track in them is left out of the video score. Empty: no guard.
    audio_codec_guard: CsvList = Field(default_factory=list)
    # pellav2 (app/ml/audio/pellav2.py): pretrained by its authors, scored on every clip.
    audio_pellav2_enabled: bool = True
    # True: pellav2 decides the audio verdict, with the thresholds in audio_pellav2_config_file
    # (written by scripts/eval_audio_detector.py); the LCNN is context, and decides only if pellav2
    # cannot run. Default since it measured better on every test set: ASVspoof 2019 LA eval, its
    # re-encoded copies and ASVspoof 5 eval (evaluation/AUDIO-PELLAV2-01*). False: the LCNN decides.
    audio_pellav2_in_verdict: bool = True
    # True: narrowband (phone / VoIP) audio that pellav2 calls fake is reported INCONCLUSIVE. Off: measured
    # on ASVspoof 5 it removed few false alarms and many detections (evaluation/QUICK-GUARDS-01). The
    # reliability note is shown either way.
    audio_narrowband_guard: bool = False
    audio_pellav2_max_windows: int = 8  # 8 x 4 s = the first 32 s of audio
    audio_pellav2_model_id: str = "Sadanie/pellav2-audio-deepfake-detector"  # or a local .pt / folder
    audio_pellav2_config_file: Path = ROOT_DIR / "paper" / "config" / "pellav2_verdict_config.json"
    # Community Forensics ViT (app/ml/commfor.py), pretrained by its authors. Its log-odds
    # weight was chosen on the dev half of the COCO + Synthbuster set
    # (evaluation/COMMFOR-02/scene_detector_eval_dev.json) and checked on the test half
    # (evaluation/E2E-01). 0 = scored and shown, not counted in the verdict.
    commfor_enabled: bool = True
    commfor_model_id: str = "OwensLab/commfor-model-384"
    commfor_weight: float = 4.0
    # A second Community Forensics expert fine-tuned on FLUX.2, GPT Image 2 and Nano Banana 2
    # (ml/training/finetune_commfor.py, calibrated on its validation split). Path relative to
    # checkpoint_dir; it is skipped if the file is missing. Used together with the original
    # at equal weight, a rule fixed before scoring the test sets (evaluation/COMMFOR-FT-01):
    # the combination called none of the 1,009 real test photos MANIPULATED (evaluation/E2E-02); without the original the fine-tuned
    # model scored 6.4 % of COCO test photos as AI (old_v3.json).
    commfor_ft_checkpoint: str = "commfor_ft_v3/model.safetensors"
    commfor_ft_weight: float = 4.0
    # Without camera metadata nothing positively shows an image came from a camera, so a
    # low score only means no detector fired. AUTHENTIC then needs a fused P(AI) below
    # this; between it and the decision band the verdict is INCONCLUSIVE. Chosen on the
    # same dev half at COMMFOR_WEIGHT=4: 99.0 % of real photos stay below it, 0.7 % of AI images.
    image_authentic_max_prob_without_camera: float = 0.02
    # TruFor splice / edit localisation (app/ml/trufor.py). Nonprofit use only (its licence);
    # set false for any commercial deployment. Shown as an unvalidated signal; it changes the
    # verdict only with TRUFOR_IN_VERDICT=true, which needs a measured threshold first.
    trufor_enabled: bool = True
    trufor_in_verdict: bool = False
    # Integrity score at which a region is reported as possibly edited: the lowest threshold
    # flagging <= 2 % of real COCO photos on the dev half (evaluation/TRUFOR-01/results.json).
    # Re-compressed social-media photos are flagged more often (10 % of accuracy_test real).
    trufor_flag_at: float = 0.8
    trufor_max_side: int = 2048  # longer images are downscaled first (GPU memory)
    trufor_weights: str = ""  # local trufor.pth.tar; empty = download once into trufor_cache_dir
    trufor_cache_dir: Path = Path.home() / ".cache" / "deepsentinel" / "trufor"

    # --- Decision thresholds ---
    fake_threshold: float = 0.5
    uncertain_band: float = 0.08

    # --- Frontend ---
    cors_origins: CsvList = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("cors_origins", "trusted_proxies", "enabled_media_types", "audio_codec_guard", mode="before")
    @classmethod
    def _split_list(cls, value: object) -> object:
        """Accept a JSON list or a comma-separated string from the environment."""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return [str(item).strip() for item in json.loads(text) if str(item).strip()]
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    @field_validator("audio_codec_guard", mode="after")
    @classmethod
    def _known_codec_families(cls, value: list[str]) -> list[str]:
        families = [item.lower() for item in value]
        unknown = sorted(set(families) - {"mp3", "aac", "opus", "resample"})
        if unknown:
            raise ValueError(f"AUDIO_CODEC_GUARD: unknown codec families {unknown}; use mp3, aac, opus or resample")
        return families

    @field_validator("enabled_media_types", mode="after")
    @classmethod
    def _known_media_types(cls, value: list[str]) -> list[str]:
        value = [item.lower() for item in value]
        unknown = sorted(set(value) - set(MEDIA_TYPES))
        if unknown:
            raise ValueError(f"ENABLED_MEDIA_TYPES has unknown entries {unknown}; allowed: {', '.join(MEDIA_TYPES)}")
        return value

    @field_validator("trusted_proxies", mode="after")
    @classmethod
    def _valid_proxies(cls, value: list[str]) -> list[str]:
        import ipaddress

        for entry in value:
            ipaddress.ip_network(entry, strict=False)  # raises on anything that is not an IP or CIDR
        return value

    @field_validator("audio_model_source", mode="after")
    @classmethod
    def _known_audio_source(cls, value: str) -> str:
        if value not in {"legacy", "lcnn_asvspoof"}:
            raise ValueError("AUDIO_MODEL_SOURCE must be 'legacy' or 'lcnn_asvspoof'")
        return value

    @field_validator(
        "storage_dir", "evidence_dir", "report_dir", "checkpoint_dir", "audio_lcnn_calibration_file",
        "audio_verdict_config_file", "audio_pellav2_config_file", mode="after",
    )
    @classmethod
    def _anchor_path(cls, value: Path) -> Path:
        """Ensure directories are absolute and anchored to the project root."""
        return value if value.is_absolute() else (ROOT_DIR / value).resolve()

    @model_validator(mode="after")
    def _reject_unsafe_production(self) -> Settings:
        """Refuse to start a production deployment with an unsafe configuration.

        Failing loudly at boot is the only reliable moment to catch these: once
        the service is serving traffic, a placeholder signing key is a silent
        authentication bypass — anyone with the repository can mint valid tokens.
        """
        if self.environment.lower() != "production":
            return self

        problems: list[str] = []
        if self.jwt_secret_key == INSECURE_JWT_SECRET:
            problems.append(
                "JWT_SECRET_KEY is still the placeholder from .env.example. Generate one with:\n"
                '    python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        elif len(self.jwt_secret_key) < MIN_JWT_SECRET_LENGTH:
            problems.append(
                f"JWT_SECRET_KEY is only {len(self.jwt_secret_key)} characters; "
                f"use at least {MIN_JWT_SECRET_LENGTH}."
            )
        if self.debug:
            problems.append("DEBUG must be false in production — debug output can leak internals.")
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must name real origins in production, never '*'.")

        if problems:
            raise InsecureConfigurationError(
                "Refusing to start: unsafe production configuration.\n\n  - "
                + "\n  - ".join(problems)
            )
        return self

    @property
    def cookie_secure(self) -> bool:
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure
        return self.environment.lower() == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def queue_enabled(self) -> bool:
        """False => inference runs inline (Celery eager mode), no Redis needed."""
        return bool(self.celery_broker_url)

    def ensure_directories(self) -> None:
        """Create the storage directories the app writes to."""
        for directory in (
            self.storage_dir,
            self.evidence_dir,
            self.report_dir,
            self.checkpoint_dir,
        ):
            Path(directory).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
