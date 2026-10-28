"""Stage 8 of the audio suite: synthesis and tampering risk, and the verdict.

Two rules, chosen by the model stage:

**Trained model** (``AUDIO_MODEL_SOURCE=lcnn_asvspoof``, the default). The
verdict is the calibrated LCNN spoof probability p against the thresholds
frozen on ASVspoof 2019 LA dev (``paper/config/frozen_audio_config.json``):
authentic below ``authentic_below``, AI-generated at or above
``flagged_at_or_above``, inconclusive in between. Glottal, coarticulation,
mains-hum, splice, container and steganography signals are computed and
reported as context with no weight: none separated bona fide from spoofed
speech on dev (paper_results/audio_heuristics_dev/signal_auc.json).
With ``AUDIO_PELLAV2_IN_VERDICT=true`` the same rule runs on the pellav2
probability, with the thresholds in ``paper/config/pellav2_verdict_config.json``.

**Hand-set rule** (``legacy``, no trained model; results are experimental):

    R_synth  = 0.50 x model stage + 0.35 x glottal anomaly + 0.15 x coarticulation anomaly
    R_tamper = 0.25 x (3 ENF splice + 2 splice-timeline flag + 2 trailing bytes + 1 steganography),
               clipped to [0.02, 0.98]

AUTHENTIC when both risks are below 0.35, flagged when either reaches 0.70,
INCONCLUSIVE in between. The weights and both thresholds were set by hand; they
were not fitted or calibrated on data, so no false-positive bound comes with
them. (Earlier versions called the decision a conformal prediction set with
alpha = 0.01 and reported likelihood ratios of 25,000 / 450 / 0.0001; none of
those numbers was computed from data, and they were removed.)
"""

from __future__ import annotations

from typing import Any

TAU_AUTHENTIC = 0.35
TAU_FLAGGED = 0.70

DECISION_RULE = (
    "Hand-set rule, not calibrated on data: authentic if synthesis and tampering risk "
    f"are both below {TAU_AUTHENTIC}, flagged if either reaches {TAU_FLAGGED}, "
    "inconclusive otherwise."
)


def compute_evidence_fusion_and_risk(
    vault_record: dict[str, Any],
    file_dna: dict[str, Any],
    signal_intel: dict[str, Any],
    glottal_physics: dict[str, Any],
    models_output: dict[str, Any],
    splicing_timeline: dict[str, Any],
    enf_environment: dict[str, Any],
    security_provenance: dict[str, Any],
    speech_semantics: dict[str, Any],
    verdict_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine the stage outputs into synthesis risk, tampering risk and a verdict.

    ``verdict_config`` (the frozen audio config) selects the trained-model rule
    when the model stage is the ASVspoof LCNN.
    """

    # ------------------------------------------------------------- 1. Synthesis risk (R_synth)
    ai_ml_prob = models_output.get("fused_ai_probability", 0.10)
    glottal_err = glottal_physics.get("composite_physiological_anomaly_score", 0.20)
    coarticulation_err = speech_semantics.get("phonemic_coarticulation_anomaly_score", 0.10)

    r_synth = float(0.50 * ai_ml_prob + 0.35 * glottal_err + 0.15 * coarticulation_err)

    # ------------------------------------------------------------- 2. Tampering risk (R_tamper)
    enf_splice = enf_environment.get("environmental_splicing_confirmed", False)
    timeline_splice = splicing_timeline.get("splicing_detected", False)
    trailing_bytes = file_dna.get("trailing_data_detected", False)
    stego_detected = security_provenance.get("steganography_forensics", {}).get("steganography_detected", False)

    tamper_signals = 0
    if enf_splice:
        tamper_signals += 3
    if timeline_splice:
        tamper_signals += 2
    if trailing_bytes:
        tamper_signals += 2
    if stego_detected:
        tamper_signals += 1

    r_tamper = float(min(0.98, max(0.02, tamper_signals * 0.25)))

    if verdict_config is not None and models_output.get("model_stage_source") in ("lcnn_asvspoof", "pellav2"):
        return _trained_model_decision(
            float(ai_ml_prob), r_tamper, verdict_config, vault_record, file_dna, glottal_physics, models_output,
            splicing_timeline, enf_environment, glottal_err, coarticulation_err,
            {"enf_splice": enf_splice, "timeline_splice": timeline_splice, "trailing_bytes": trailing_bytes,
             "stego": stego_detected},
        )

    # ------------------------------------------------------------- 3. Decision (fixed thresholds)
    decision_set = []
    if r_synth < TAU_AUTHENTIC and r_tamper < TAU_AUTHENTIC:
        decision_set.append("AUTHENTIC")
    elif r_synth >= TAU_FLAGGED or r_tamper >= TAU_FLAGGED:
        if r_synth >= TAU_FLAGGED:
            decision_set.append("AI_GENERATED")
        if r_tamper >= TAU_FLAGGED:
            decision_set.append("SPLICED_TAMPERED")
    else:
        decision_set = ["AUTHENTIC", "AI_GENERATED"]  # between the thresholds

    is_inconclusive = len(decision_set) > 1

    overall_fake_prob = max(r_synth, r_tamper)
    if is_inconclusive:
        verdict = "INCONCLUSIVE"
    elif overall_fake_prob >= TAU_FLAGGED:
        verdict = "AI_GENERATED" if r_synth >= r_tamper else "MANIPULATED"
    else:
        verdict = "AUTHENTIC"

    # ------------------------------------------------------------- 4. Evidence graph
    graph = _build_evidence_graph(
        vault_record, file_dna, glottal_physics, models_output, splicing_timeline, enf_environment, verdict
    )

    # ------------------------------------------------------------- 5. Signals that fired
    flagged_signals = []
    if r_synth >= 0.65:
        flagged_signals.append("Synthesis risk at or above 0.65")
    if glottal_err >= 0.60:
        flagged_signals.append("Glottal anomaly score at or above 0.60 (heuristic, unvalidated)")
    if enf_splice:
        flagged_signals.append("Mains-hum (ENF) phase discontinuity (heuristic, unvalidated)")
    if timeline_splice:
        flagged_signals.append("Splice-timeline boundary spikes (heuristic, unvalidated)")
    if trailing_bytes:
        flagged_signals.append(f"Container: {file_dna.get('trailing_bytes_count')} bytes appended after the audio data")
    if stego_detected:
        flagged_signals.append("Possible steganographic payload (heuristic, unvalidated)")

    return {
        "final_verdict": verdict,
        "calibrated_fake_probability": round(overall_fake_prob, 4),
        "generative_ai_risk_score": round(r_synth, 4),
        "structural_tampering_risk_score": round(r_tamper, 4),
        "decision_set": decision_set,
        "decision_rule": DECISION_RULE,
        "is_inconclusive": is_inconclusive,
        "flagged_signals_count": len(flagged_signals),
        "flagged_signals": flagged_signals,
        "verdict_source": "hand_set_rule",
        "evidence_graph": graph,
    }


def _trained_model_decision(
    p: float,
    r_tamper: float,
    config: dict[str, Any],
    vault_record: dict[str, Any],
    file_dna: dict[str, Any],
    glottal_physics: dict[str, Any],
    models_output: dict[str, Any],
    splicing_timeline: dict[str, Any],
    enf_environment: dict[str, Any],
    glottal_err: float,
    coarticulation_err: float,
    flags: dict[str, bool],
) -> dict[str, Any]:
    """Verdict from the trained model's probability alone (LCNN or pellav2); heuristics are context."""
    low, high = float(config["authentic_below"]), float(config["flagged_at_or_above"])
    if p >= high:
        verdict, decision_set = "AI_GENERATED", ["AI_GENERATED"]
    elif p < low:
        verdict, decision_set = "AUTHENTIC", ["AUTHENTIC"]
    else:
        verdict, decision_set = "INCONCLUSIVE", ["AUTHENTIC", "AI_GENERATED"]

    context = []
    if glottal_err >= 0.60:
        context.append("Glottal anomaly score at or above 0.60 (heuristic, unvalidated; no weight)")
    if flags["enf_splice"]:
        context.append("Mains-hum (ENF) phase discontinuity (heuristic, unvalidated; no weight)")
    if flags["timeline_splice"]:
        context.append("Splice-timeline boundary spikes (heuristic, unvalidated; no weight)")
    if flags["trailing_bytes"]:
        context.append(f"Container: {file_dna.get('trailing_bytes_count')} bytes appended after the audio data (no weight)")
    if flags["stego"]:
        context.append("Possible steganographic payload (heuristic, unvalidated; no weight)")

    model_name = "pellav2" if models_output.get("model_stage_source") == "pellav2" else "LCNN"
    signals = [f"{model_name} spoof probability {p * 100:.1f}% (threshold {config['threshold']:.3f}, "
               f"inconclusive band {low:.3f}-{high:.3f})"]
    return {
        "final_verdict": verdict,
        "calibrated_fake_probability": round(p, 4),
        "generative_ai_risk_score": round(p, 4),
        "structural_tampering_risk_score": round(r_tamper, 4),
        "decision_set": decision_set,
        "decision_rule": config["decision_rule"],
        "decision_threshold": float(config["threshold"]),
        "uncertain_band": float(config["inconclusive_band"]),
        "is_inconclusive": verdict == "INCONCLUSIVE",
        "flagged_signals_count": len(context),
        "flagged_signals": signals + context,
        "context_signals": {
            "note": "computed and shown, no weight in the verdict (none separated bona fide from spoof on dev)",
            "structural_tampering_risk": round(r_tamper, 4),
            "glottal_anomaly": round(float(glottal_err), 4),
            "coarticulation_anomaly": round(float(coarticulation_err), 4),
            "hand_set_rule_score": models_output.get("legacy_fused_ai_probability"),
        },
        "verdict_source": models_output.get("model_stage_source"),
        "evidence_graph": _build_evidence_graph(
            vault_record, file_dna, glottal_physics, models_output, splicing_timeline, enf_environment, verdict,
            trained_model_only=True,
        ),
    }


def _build_evidence_graph(
    vault: dict, dna: dict, phys: dict, models: dict, splice: dict, enf: dict, verdict: str,
    trained_model_only: bool = False,
) -> dict[str, Any]:
    """Which stage outputs feed the verdict. Edges carry no weights: see the module docstring."""
    model_label = models.get("model_stage_label") or "trained model"
    glottal = phys.get("composite_physiological_anomaly_score", 0)
    nodes = [
        {"id": "file_root", "label": "Audio file", "type": "root", "status": "NEUTRAL"},
        {"id": "vault_node", "label": f"File hashes: {vault.get('evidence_id', 'EVID')}", "type": "integrity", "status": "RECORDED"},
        {"id": "dna_node", "label": f"Container: {dna.get('container_format')} / {dna.get('codec')}", "type": "container", "status": "ALERT" if dna.get("trailing_data_detected") else "NORMAL"},
        {"id": "glottal_node", "label": f"Glottal anomaly {glottal:.2f} (heuristic, unvalidated)", "type": "physics", "status": "ALERT" if glottal > 0.6 else "NORMAL"},
        {"id": "enf_node", "label": f"Mains hum (max slip {enf.get('enf_forensics', {}).get('max_phase_slip_degrees', 0):.1f} deg; heuristic, unvalidated)", "type": "environment", "status": "ALERT" if enf.get("environmental_splicing_confirmed") else "NORMAL"},
        {"id": "model_node", "label": f"Model stage {models.get('fused_ai_probability', 0) * 100:.1f}% ({model_label})", "type": "model", "status": "ALERT" if models.get("fused_ai_probability", 0) > 0.65 else "NORMAL"},
        {"id": "splice_node", "label": f"Splice timeline: {splice.get('first_order_f1_spikes_count', 0)} spikes (heuristic, unvalidated)", "type": "temporal", "status": "ALERT" if splice.get("splicing_detected") else "NORMAL"},
        {"id": "verdict_node", "label": f"Verdict: {verdict}", "type": "verdict", "status": "CRITICAL" if verdict in ("AI_GENERATED", "MANIPULATED") else ("INCONCLUSIVE" if verdict == "INCONCLUSIVE" else "SECURE")},
    ]

    if trained_model_only:
        return {
            "nodes": nodes,
            "edges": [
                {"source": "file_root", "target": "model_node", "label": "model stage"},
                {"source": "model_node", "target": "verdict_node", "label": "decides the verdict"},
                *({"source": "file_root", "target": node, "label": "context only"}
                  for node in ("vault_node", "dna_node", "glottal_node", "enf_node", "splice_node")),
            ],
        }

    edges = [
        {"source": "file_root", "target": "vault_node", "label": "hashing"},
        {"source": "file_root", "target": "dna_node", "label": "container parsing"},
        {"source": "file_root", "target": "glottal_node", "label": "inverse filtering"},
        {"source": "file_root", "target": "enf_node", "label": "mains-hum tracking"},
        {"source": "file_root", "target": "model_node", "label": "model stage"},
        {"source": "file_root", "target": "splice_node", "label": "segment comparison"},
        {"source": "model_node", "target": "verdict_node", "label": "synthesis risk"},
        {"source": "glottal_node", "target": "verdict_node", "label": "synthesis risk"},
        {"source": "dna_node", "target": "verdict_node", "label": "tampering risk"},
        {"source": "enf_node", "target": "verdict_node", "label": "tampering risk"},
        {"source": "splice_node", "target": "verdict_node", "label": "tampering risk"},
    ]

    return {"nodes": nodes, "edges": edges}
