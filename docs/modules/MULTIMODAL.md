# Module: Multimodal Evidence Correlation

## 1. Purpose
The Multimodal Evidence Correlation module bridges independent analysis streams (visual frames, audio speech, container metadata, temporal timelines) to detect cross-modal inconsistencies that single-modality detectors miss, such as lip-sync divergence, voice-identity mismatches, and environmental acoustic-lighting mismatches.

---

## 2. Input
- **Video Stream:** Temporal frame sequence and visual facial landmarks.
- **Audio Stream:** Demuxed audio track, voice activity intervals, and phoneme timings.
- **Metadata Context:** Container timestamps, encoding parameters, and device tags.

---

## 3. Processing Pipeline

1. **Cross-Modal Demuxing & Alignment:** Synchronizes audio and visual frames to a common temporal timeline millisecond by millisecond.
2. **Audio-Visual Lip Synchronization:**
   - Detects mouth aperture (vertical/horizontal lip distance) across video frames.
   - Extracts speech energy envelope and phonetic formant transitions from the audio track.
   - Computes cross-correlation between mouth movements and vocal tract acoustics to identify desynchronization indicative of Wav2Lip or audio dubbing.
3. **Identity & Pitch Biometrics:** Correlates detected visual facial demographics/age with acoustic fundamental frequency ($F_0$) to identify obvious voice impersonation mismatches.
4. **Environmental Consistency Check:**
   - Evaluates lighting source direction from facial shadows against acoustic reverberation room acoustics (e.g., bright outdoor sunlight paired with an echoic tiled room impulse response).
5. **Cross-Stream Evidence Fusion:** Applies calibrated matrix weighting across visual scores, audio scores, and cross-modal correlation scores to calculate an overall multimodal confidence score.

---

## 4. Output
- **Multimodal Verdict:** `CONSISTENT_AUTHENTIC`, `CROSS_MODAL_MISMATCH`, `DUBBED_OR_LIP_SYNCED`, or `UNCERTAIN`.
- **Audio-Visual Sync Score:** Cross-correlation coefficient $(-1.0 \dots +1.0)$.
- **Lag Offset:** Temporal offset in milliseconds between visual lip movement and audio speech onset.
- **Correlation Timeline Plot:** Graph showing audio energy envelope plotted against mouth opening distance.

---

## 5. Evidence Generated
- Cross-modal synchronization coefficient.
- Audio-visual lag estimation (e.g., $+120\text{ ms}$ voice leading visual lips).
- Combined multimodal risk score.
- Structured breakdown of individual vs. correlated risk signals.

---

## 6. Limitations
- Natural transmission delay or poor container multiplexing in broadcast video can introduce minor audio-video offsets unrelated to deepfakes.
- Videos where the speaker's mouth is partially obscured (e.g., microphones, masks, hands) limit lip landmark precision.
- Rapid camera cuts and background speakers can complicate cross-modal correlation.
