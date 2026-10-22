"""P1: the backend must not name models that never run, or claim standards compliance.

The audio suite once reported "WavLM layer 18", "Whisper layer 4" and
"Sinc-RawNet" scores that no such model produced, and the PDF and audio vault
claimed SWGDE, ISO/IEC 27037/27042 and Daubert compliance. This test keeps
those names out of ``backend/app`` (the legacy copy ``app/ml_v1`` is excluded
until it is deleted).
"""

from __future__ import annotations

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
BANNED = re.compile(
    r"wavlm|whisper|sinc-?rawnet|swgde|daubert|27037|27042|judicial|write.?blocker|cybercrime complaint",
    re.IGNORECASE,
)


def test_no_fake_model_names_or_standards_claims_in_backend_app():
    hits = []
    for path in sorted(APP.rglob("*.py")):
        if "ml_v1" in path.relative_to(APP).parts:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if BANNED.search(line):
                hits.append(f"{path.relative_to(APP.parent)}:{number}: {line.strip()[:100]}")
    assert not hits, "\n".join(hits)
