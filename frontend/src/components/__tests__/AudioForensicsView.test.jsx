import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AudioForensicsView from '../AudioForensicsView'
import realAudioResult from './fixtures/real_audio_result.json'

const mockAudioResult = {
  id: 'job-audio-123',
  verdict: 'AI_GENERATED',
  fake_probability: 0.912,
  confidence: 0.95,
  model_name: 'LCNN (LFCC), ASVspoof 2019 LA',
  model_version: 'audio-lcnn-dev-seed2',
  weights_status: 'TRAINED',
  evidence: {
    media: 'audio',
    dominant_threat: 'Synthetic Neural TTS (LCNN)',
    threat_code: 'TTS_SYNTHETIC',
    decision_threshold: 0.5,
    uncertain_band: 0.08,
    decision_rule: 'Calibrated Platt-scaled mean window logit from LCNN trained on ASVspoof 2019 LA LFCC features.',
    segments_analysed: 2,
    flagged_segments: 2,
    segment_scores_source: 'lcnn_asvspoof',
    segment_scores: [
      {
        segment_index: 0,
        start_s: 0.0,
        end_s: 4.0,
        fake_probability: 0.912,
        status: 'FLAGGED',
        source: 'lcnn_asvspoof',
        reasons: ['Exceeded decision threshold']
      },
      {
        segment_index: 1,
        start_s: 4.0,
        end_s: 7.2,
        fake_probability: 0.895,
        status: 'FLAGGED',
        source: 'lcnn_asvspoof',
        reasons: ['Exceeded decision threshold']
      }
    ],
    glottal_physics: {
      composite_physiological_anomaly_score: 0.72,
      vocal_jitter_local_pct: 1.45,
      vocal_shimmer_local_db: 0.88,
    },
    enf_environment: {
      grid_frequency_hz: 50.02,
      enf_forensics: { max_phase_slip_degrees: 0.0 },
      environmental_splicing_confirmed: false,
    },
    splicing_timeline: {
      splicing_detected: false,
      first_order_f1_spikes_count: 0,
    },
    file_dna: {
      container_format: 'RIFF/WAV',
      codec: 'PCM (Uncompressed)',
      trailing_data_detected: false,
    },
    signal_intel: {
      sample_rate: 16000,
      duration_seconds: 7.2,
      time_domain: { dynamic_range_db: 48.2 },
      clipping_analysis: { clipping_detected: false },
    },
    fusion_decision: {
      final_verdict: 'AI_GENERATED',
      decision_rule: 'Calibrated Platt-scaled mean window logit from LCNN trained on ASVspoof 2019 LA LFCC features.',
      decision_threshold: 0.5,
      uncertain_band: 0.08,
      context_signals: {
        note: 'Carried no weight in the verdict; shown as context only.',
        structural_tampering_risk: 0.15,
        glottal_anomaly: 0.72,
        coarticulation_anomaly: 0.20,
        hand_set_rule_score: 0.45,
      },
    },
    pipeline_modules: [
      { stage: 1, name: 'Secure Ingestion Vault', status: 'PASSED', duration_ms: 8, summary: 'SHA-256 verified' },
      { stage: 2, name: 'Audio File DNA & Container Forensics', status: 'PASSED', duration_ms: 22, summary: 'RIFF/WAV valid' },
      { stage: 3, name: 'Signal Intelligence & Acoustic Telemetry', status: 'PASSED', duration_ms: 55, summary: 'SNR: 24dB' },
      { stage: 4, name: 'Physiological Glottal Flow & VoiceRadar Physics', status: 'ANOMALY_DETECTED', duration_ms: 85, summary: 'Glottal Qo anomaly' },
      { stage: 5, name: 'Content & Phonemic Coarticulation', status: 'PASSED', duration_ms: 40, summary: '135 WPM' },
      { stage: 6, name: 'Trained LCNN Neural Classifier', status: 'AI_FLAGGED', duration_ms: 290, summary: 'LCNN: 91.2%' },
      { stage: 7, name: 'Environmental & ENF Grid Forensics', status: 'PASSED', duration_ms: 60, summary: '50Hz grid intact' },
      { stage: 8, name: 'Evidence Fusion & Decision Engine', status: 'AI_FLAGGED', duration_ms: 30, summary: 'Trained model verdict' },
    ],
  },
}

describe('AudioForensicsView Trained Model & Timeline Layout', () => {
  it('renders trained-model score, verdict, and per-window timeline as the main result', () => {
    render(<AudioForensicsView result={mockAudioResult} />)

    // 1. Trained Model Hero Result Card
    expect(screen.getByText('Trained Model Score & Verdict')).toBeInTheDocument()
    expect(screen.getByText(/LCNN \(LFCC\), ASVspoof 2019 LA/i)).toBeInTheDocument()
    expect(screen.getAllByText('AI_GENERATED').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('91.2%').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('0.500')).toBeInTheDocument()
    expect(screen.getByText(/±0.080 band/i)).toBeInTheDocument()
    expect(screen.getAllByText('ASVspoof 2019 LA').length).toBeGreaterThanOrEqual(1)

    // 2. Per-Window Timeline Card
    expect(screen.getByText('Per-Window Timeline (Trained Model)')).toBeInTheDocument()
    expect(screen.getByText(/Calibrated ASVspoof LCNN classification across sliding 4.0s temporal windows/i)).toBeInTheDocument()
    expect(screen.getByText('Temporal Window Status Map')).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText(/0.00s – 4.00s/i)).toBeInTheDocument()
    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText(/4.00s – 7.20s/i)).toBeInTheDocument()
    expect(screen.getAllByText('LCNN (LFCC)').length).toBeGreaterThanOrEqual(1)
  })

  it('moves glottal, ENF, and signal checks under "Supporting signals (unvalidated)"', () => {
    render(<AudioForensicsView result={mockAudioResult} />)

    // Supporting signals header & scope note
    expect(screen.getByText('Supporting signals (unvalidated)')).toBeInTheDocument()
    expect(screen.getByText(/These heuristic and physical checks carry no weight in the verdict/i)).toBeInTheDocument()

    // 3 Heuristic checks labeled unvalidated
    expect(screen.getByText('Glottal Flow & Voice Aerodynamics')).toBeInTheDocument()
    expect(screen.getByText('Electrical Network Frequency (ENF)')).toBeInTheDocument()
    expect(screen.getByText('Signal & Splice Integrity')).toBeInTheDocument()
    expect(screen.getByText('Container & Custody')).toBeInTheDocument()

    const unvalidatedBadges = screen.getAllByText('Unvalidated Heuristic')
    expect(unvalidatedBadges.length).toBe(3)
    expect(screen.getByText('Context Only')).toBeInTheDocument()
  })

  it('removes typology breakdown and generator-family panels', () => {
    render(<AudioForensicsView result={mockAudioResult} />)

    expect(screen.queryByText(/Speech Synthesis Typology Breakdown/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Generator Family Attribution/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/typology/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/generator family/i)).not.toBeInTheDocument()
  })

  it('renders a real response payload from the ml/audio-wire backend', () => {
    render(<AudioForensicsView result={realAudioResult} />)

    // Main result card with real values
    expect(screen.getByText('Trained Model Score & Verdict')).toBeInTheDocument()
    expect(screen.getAllByText('AUTHENTIC').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('0.0%').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('0.497')).toBeInTheDocument()

    // Real per-window timeline
    expect(screen.getByText('Per-Window Timeline (Trained Model)')).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText(/0.00s – 3.00s/i)).toBeInTheDocument()

    // Real supporting signals with unvalidated badges
    expect(screen.getByText('Supporting signals (unvalidated)')).toBeInTheDocument()
    expect(screen.getByText('Glottal Flow & Voice Aerodynamics')).toBeInTheDocument()
    expect(screen.getByText('Electrical Network Frequency (ENF)')).toBeInTheDocument()
    expect(screen.getByText('Signal & Splice Integrity')).toBeInTheDocument()

    // Typology and generator family are absent
    expect(screen.queryByText(/typology/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/generator family/i)).not.toBeInTheDocument()
  })
})

describe('AudioForensicsView Pipeline SubTab', () => {
  it('renders pipeline tab with 8-stage architecture, charts, and audit trail', () => {
    render(<AudioForensicsView result={mockAudioResult} activeSubTab="pipeline" setActiveSubTab={() => {}} />)

    expect(screen.getByText(/8-Stage Acoustic Forensic Architecture/i)).toBeInTheDocument()
    expect(screen.getByText(/Stage Latency Waterfall/i)).toBeInTheDocument()
    expect(screen.getByText(/Acoustic Forensic Risk Radar/i)).toBeInTheDocument()
    expect(screen.getByText(/Linear Forensic Audit Trail/i)).toBeInTheDocument()
  })

  it('allows clicking an audio stage node or card to inspect deep telemetry', () => {
    const handleSubTabChange = vi.fn()
    render(<AudioForensicsView result={mockAudioResult} activeSubTab="pipeline" setActiveSubTab={handleSubTabChange} />)

    const stage4Button = screen.getByRole('button', { name: /Stage 4:/i })
    fireEvent.click(stage4Button)

    expect(screen.getByText(/Stage 4: Physiological Glottal Flow & VoiceRadar Physics/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Physical Forensics/i).length).toBeGreaterThanOrEqual(1)
  })

  it('provides navigation button to switch to corresponding deep lab', () => {
    const handleSubTabChange = vi.fn()
    render(<AudioForensicsView result={mockAudioResult} activeSubTab="pipeline" setActiveSubTab={handleSubTabChange} />)

    const jumpBtn = screen.getByRole('button', { name: /Jump to Secure Lab/i })
    fireEvent.click(jumpBtn)
    expect(handleSubTabChange).toHaveBeenCalledWith('security')
  })
})

describe('AudioForensicsView with pellav2', () => {
  const pellav2 = {
    prob: 0.9731, n_windows: 2, window_probs: [0.9612, 0.985], model: 'pellav2 (w2v-BERT 2.0)',
    windows: [{ index: 0, start_s: 0, end_s: 4, probability: 0.9612 }, { index: 1, start_s: 4, end_s: 7.2, probability: 0.985 }]
  }

  it('shows pellav2 as unvalidated context when the LCNN decides', () => {
    const result = { ...mockAudioResult, evidence: { ...mockAudioResult.evidence, models_output: { pellav2 } } }
    render(<AudioForensicsView result={result} activeSubTab="summary" setActiveSubTab={() => {}} />)

    const context = screen.getByTestId('pellav2-context')
    expect(context).toHaveTextContent(/pellav2 \(w2v-BERT 2\.0\): 97\.3%/)
    expect(context).toHaveTextContent(/not in the verdict/)
    expect(screen.getAllByText('LCNN (LFCC)').length).toBeGreaterThanOrEqual(1)
  })

  it('names pellav2 as the model when it decides the verdict', () => {
    const segments = mockAudioResult.evidence.segment_scores.map(s => ({ ...s, source: 'pellav2' }))
    const result = {
      ...mockAudioResult,
      model_name: 'pellav2 (w2v-BERT 2.0)',
      evidence: {
        ...mockAudioResult.evidence,
        segment_scores: segments,
        segment_scores_source: 'pellav2',
        models_output: { pellav2 },
        fusion_decision: { ...(mockAudioResult.evidence.fusion_decision || {}), verdict_source: 'pellav2' }
      }
    }
    render(<AudioForensicsView result={result} activeSubTab="summary" setActiveSubTab={() => {}} />)

    expect(screen.queryByTestId('pellav2-context')).not.toBeInTheDocument()
    expect(screen.getAllByText('pellav2').length).toBe(2)
    expect(screen.queryByText('LCNN (LFCC)')).not.toBeInTheDocument()
    expect(screen.getByText(/pellav2 classification across consecutive 4\.0s windows/)).toBeInTheDocument()
  })
})
