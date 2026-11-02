"""Audio evidence charts close their figures even when saving fails.

A failed savefig used to skip plt.close, so each failure leaked several large figures; the
end-to-end audio evaluation grew to about 34 GB per process this way (round 4).
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def test_failed_save_leaves_no_open_figure(tmp_path):
    from app.ml.audio.signal_lab import _render_waveform_profile

    sr = 16000
    wave = np.sin(np.linspace(0, 200, sr)).astype(np.float32)
    before = set(plt.get_fignums())
    missing = tmp_path / "no-such-folder" / "wave.png"
    try:
        _render_waveform_profile(wave, sr, 1.0, missing)
    except Exception:
        pass
    assert set(plt.get_fignums()) == before


def test_successful_save_still_writes_the_file(tmp_path):
    from app.ml.audio.signal_lab import _render_waveform_profile

    sr = 16000
    out = tmp_path / "wave.png"
    _render_waveform_profile(np.zeros(sr, dtype=np.float32), sr, 1.0, out)
    assert out.exists() and out.stat().st_size > 0
