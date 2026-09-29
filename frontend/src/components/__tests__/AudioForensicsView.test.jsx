import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AudioForensicsView from '../AudioForensicsView'

const mockAudioResult = {
  id: 'job-audio-123',
  verdict: 'AI_GENERATED',
  fake_probability: 0.91,
  confidence: 0.95,
  evidence: {
    media: 'audio',
    dominant_threat: 'Synthetic Neural TTS (WavLM/RawNet)',
    threat_code: 'TTS_SYNTHETIC',
    pipeline_modules: [
      { stage: 1, name: 'Secure Ingestion Vault', status: 'PASSED', duration_ms: 8, summary: 'SHA-256 verified' },
      { stage: 2, name: 'Audio File DNA & Container Forensics', status: 'PASSED', duration_ms: 22, summary: 'RIFF/WAV valid' },
      { stage: 3, name: 'Signal Intelligence & Acoustic Telemetry', status: 'PASSED', duration_ms: 55, summary: 'SNR: 24dB' },
      { stage: 4, name: 'Physiological Glottal Flow & VoiceRadar Physics', status: 'ANOMALY_DETECTED', duration_ms: 85, summary: 'Glottal Qo anomaly' },
      { stage: 5, name: 'Content & Phonemic Coarticulation', status: 'PASSED', duration_ms: 40, summary: '135 WPM' },
      { stage: 6, name: 'Multi-Model ML & Intermediate SSL Probing', status: 'AI_FLAGGED', duration_ms: 290, summary: 'WavLM: 92%' },
      { stage: 7, name: 'Environmental & ENF Grid Forensics', status: 'PASSED', duration_ms: 60, summary: '50Hz grid intact' },
      { stage: 8, name: 'Evidence Fusion & Conformal Risk Engine', status: 'ANOMALY_DETECTED', duration_ms: 30, summary: 'Risk 91%' },
    ],
  },
}

describe('AudioForensicsView Pipeline', () => {
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
    
    // Click on Stage 4 node
    const stage4Button = screen.getByRole('button', { name: /Stage 4:/i })
    fireEvent.click(stage4Button)

    expect(screen.getByText(/Stage 4: Physiological Glottal Flow & VoiceRadar Physics/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Physical Forensics/i).length).toBeGreaterThanOrEqual(1)
  })

  it('provides navigation button to switch to corresponding deep lab', () => {
    const handleSubTabChange = vi.fn()
    render(<AudioForensicsView result={mockAudioResult} activeSubTab="pipeline" setActiveSubTab={handleSubTabChange} />)

    // Stage 1 default is active, should have jump button
    const jumpBtn = screen.getByRole('button', { name: /Jump to Secure Lab/i })
    fireEvent.click(jumpBtn)
    expect(handleSubTabChange).toHaveBeenCalledWith('security')
  })
})
