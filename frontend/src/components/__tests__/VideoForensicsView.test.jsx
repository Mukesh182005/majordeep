import React from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import VideoForensicsView, { VIDEO_PIPELINE_STAGES } from '../VideoForensicsView'

const mockVideoResult = {
  id: 'job-video-123',
  verdict: 'MANIPULATED',
  fake_probability: 0.88,
  confidence: 0.94,
  evidence: {
    media: 'video',
    dominant_threat: 'AI Generative Synthesis (Veo/Sora)',
    threat_code: 'AI_SYNTHESIS',
    processing_ms: 1250,
    pipeline_modules: [
      { stage: 1, name: 'Container & Bitstream Forensics', status: 'PASSED', duration_ms: 12, desc: 'ISO format valid' },
      { stage: 2, name: 'Scene & Shot Boundary Segmentation', status: 'PASSED', duration_ms: 45, desc: '1 scene' },
      { stage: 3, name: 'Spatial Neural & Generative AI Backbone', status: 'AI_FLAGGED', duration_ms: 120, desc: 'AI artifacts detected' },
      { stage: 4, name: '28-Module Image Forensic Engine', status: 'PASSED', duration_ms: 110, desc: 'Keyframe ELA clean' },
      { stage: 5, name: 'Temporal Jitter & Facial Dynamics', status: 'PASSED', duration_ms: 30, desc: 'Jitter 0.05' },
      { stage: 6, name: 'Remote Photoplethysmography (rPPG)', status: 'INCONCLUSIVE', duration_ms: 25, desc: 'Short clip' },
      { stage: 7, name: 'Spatio-Temporal 4D Tensor Dynamics', status: 'PASSED', duration_ms: 80, desc: 'Normal 4D flow' },
      { stage: 8, name: 'LipForensics Articulatory Kinematics', status: 'INSUFFICIENT_FACE_FRAMES', duration_ms: 10, desc: 'No speech' },
      { stage: 9, name: 'Optical Flow Motion Decomposition', status: 'ANOMALY_DETECTED', duration_ms: 95, desc: 'Vector anomaly' },
      { stage: 10, name: 'Acoustic Speech & Cross-Modal Lip-Sync', status: 'PASSED', duration_ms: 15, desc: 'Audio clean' },
      { stage: 11, name: 'AI Generator Attribution Engine', status: 'AI_FLAGGED', duration_ms: 60, desc: 'Veo signature 98%' },
    ],
  },
}

describe('VideoForensicsView', () => {
  it('renders summary tab with 11-stage modular forensic pipeline overview', () => {
    render(<VideoForensicsView result={mockVideoResult} activeSubTab="summary" setActiveSubTab={() => {}} />)
    expect(screen.getByText('Modular Forensic Pipeline Execution (11 Stages)')).toBeInTheDocument()
    expect(screen.getByText('Container & Bitstream Forensics')).toBeInTheDocument()
    expect(screen.getByText('AI Generator Attribution Engine')).toBeInTheDocument()
  })

  it('renders pipeline tab without crashing and shows workflow diagram and 11 stages', () => {
    render(<VideoForensicsView result={mockVideoResult} activeSubTab="pipeline" setActiveSubTab={() => {}} />)
    expect(screen.getByText(/11-Stage Multi-Modal Pipeline Architecture/i)).toBeInTheDocument()
    expect(screen.getByText(/Stage Execution Latency Waterfall/i)).toBeInTheDocument()
    expect(screen.getByText(/Multi-Disciplinary Forensic Risk Radar/i)).toBeInTheDocument()
    expect(screen.getByText(/11-Stage Forensic Audit Trail/i)).toBeInTheDocument()
  })

  it('allows clicking a stage card to expand detailed telemetry diagnostics', () => {
    render(<VideoForensicsView result={mockVideoResult} activeSubTab="pipeline" setActiveSubTab={() => {}} />)
    const stage11 = screen.getByText(/Stage 11: AI Generator Attribution Engine/i)
    fireEvent.click(stage11)
    expect(screen.getByText(/Diagnostic Findings & Evidentiary Signal/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Veo signature 98%/i).length).toBeGreaterThanOrEqual(1)
  })
})
