import { describe, expect, it } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import VideoForensicsView from '../VideoForensicsView'
import realVideoFaceswapResult from './fixtures/real_video_faceswap_result.json'
import realVideoNofaceResult from './fixtures/real_video_noface_result.json'
import realVideoFaceswapDeepfake from './fixtures/real_video_faceswap_deepfake.json'

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
      { stage: 5, name: 'Temporal Jitter & Facial Dynamics (unvalidated)', status: 'PASSED', duration_ms: 30, desc: 'Jitter 0.05' },
      { stage: 6, name: 'Remote Photoplethysmography (rPPG) (unvalidated)', status: 'INCONCLUSIVE', duration_ms: 25, desc: 'Short clip' },
      { stage: 7, name: 'Spatio-Temporal 4D Tensor Dynamics (unvalidated)', status: 'PASSED', duration_ms: 80, desc: 'Normal 4D flow' },
      { stage: 8, name: 'LipForensics Articulatory Kinematics (unvalidated)', status: 'INSUFFICIENT_FACE_FRAMES', duration_ms: 10, desc: 'No speech' },
      { stage: 9, name: 'Optical Flow Motion Decomposition (unvalidated)', status: 'ANOMALY_DETECTED', duration_ms: 95, desc: 'Vector anomaly' },
      { stage: 10, name: 'Acoustic Speech & Cross-Modal Lip-Sync', status: 'PASSED', duration_ms: 15, desc: 'Audio clean' },
      { stage: 11, name: 'AI Generator Attribution (unvalidated)', status: 'AI_FLAGGED', duration_ms: 60, desc: 'Veo signature 98%' },
    ],
  },
}

describe('VideoForensicsView', () => {
  it('renders summary tab with 11-stage modular forensic pipeline overview', () => {
    render(<VideoForensicsView result={mockVideoResult} activeSubTab="summary" setActiveSubTab={() => {}} />)
    expect(screen.getByText('Modular Forensic Pipeline Execution (11 Stages)')).toBeInTheDocument()
    expect(screen.getByText('Container & Bitstream Forensics')).toBeInTheDocument()
    expect(screen.getAllByText(/AI Generator Attribution/i).length).toBeGreaterThanOrEqual(1)
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
    const stage11 = screen.getByText(/Stage 11: AI Generator Attribution/i)
    fireEvent.click(stage11)
    expect(screen.getByText(/Diagnostic Findings & Evidentiary Signal/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Veo signature 98%/i).length).toBeGreaterThanOrEqual(1)
  })

  it('renders per-track scores and timeline with a real response from ml/faceswap-wire backend', () => {
    render(<VideoForensicsView result={realVideoFaceswapResult} activeSubTab="summary" setActiveSubTab={() => {}} />)

    // Check Face-Swap Model Forensics card
    expect(screen.getByText('Trained Face-Swap Model Forensics')).toBeInTheDocument()
    expect(screen.getByText('Per-Track Scores (1 Track)')).toBeInTheDocument()
    expect(screen.getByText('Face Track #0')).toBeInTheDocument()
    expect(screen.getByText('Track Score (Top 25% Mean)')).toBeInTheDocument()

    // Check segment timeline from the new response
    expect(screen.getByText('Temporal Segment Timeline (from model response)')).toBeInTheDocument()
    expect(screen.getByText('00:00 - 00:02')).toBeInTheDocument()
    expect(screen.getAllByText(/Coherent face track 0/i).length).toBeGreaterThanOrEqual(1)
  })

  it('labels generator attribution and other heuristics as unvalidated', () => {
    render(<VideoForensicsView result={realVideoFaceswapResult} activeSubTab="summary" setActiveSubTab={() => {}} />)

    // Check generator attribution labeled unvalidated
    expect(screen.getByText('AI Generator Attribution (unvalidated)')).toBeInTheDocument()
    expect(screen.getByText(/unvalidated heuristic: hand-set profiles, not tested on labelled video/i)).toBeInTheDocument()
    expect(screen.getAllByText('UNVALIDATED HEURISTIC').length).toBeGreaterThanOrEqual(1)

    // Check temporal heuristics labeled unvalidated
    expect(screen.getByText('Temporal Video Dynamics (unvalidated)')).toBeInTheDocument()
    expect(screen.getByText('Farneback Flow (unvalidated)')).toBeInTheDocument()
  })

  it('says "No face found: face-swap check not applicable." when no face track exists', () => {
    render(<VideoForensicsView result={realVideoNofaceResult} activeSubTab="summary" setActiveSubTab={() => {}} />)

    expect(screen.getByText('No face found: face-swap check not applicable.')).toBeInTheDocument()
    expect(screen.queryByText(/Per-Track Scores/i)).not.toBeInTheDocument()
  })

  it('renders multiple face tracks and flagged status on deepfake video', () => {
    render(<VideoForensicsView result={realVideoFaceswapDeepfake} activeSubTab="summary" setActiveSubTab={() => {}} />)

    expect(screen.getByText('Per-Track Scores (2 Tracks)')).toBeInTheDocument()
    expect(screen.getByText('Face Track #0')).toBeInTheDocument()
    expect(screen.getByText('Face Track #1')).toBeInTheDocument()
    expect(screen.getAllByText('FLAGGED').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Track 0 face-swap score: 89.2%/i).length).toBeGreaterThanOrEqual(1)
  })

  it('renders per-track scores and timeline on the timeline tab', () => {
    render(<VideoForensicsView result={realVideoFaceswapDeepfake} activeSubTab="timeline" setActiveSubTab={() => {}} />)

    expect(screen.getByText('Trained Face-Swap Model Forensics')).toBeInTheDocument()
    expect(screen.getByText('Per-Track Scores (2 Tracks)')).toBeInTheDocument()
    expect(screen.getByText('Temporal Segment Timeline (from model response)')).toBeInTheDocument()
  })
})


describe('VideoForensicsView with GenD', () => {
  it('shows the GenD mean / max and whether it is in the verdict', () => {
    const result = {
      ...realVideoFaceswapResult,
      evidence: { ...realVideoFaceswapResult.evidence, gend_face_mean: 0.82, gend_face_max: 0.97, gend_faces_scored: 24,
                  gend_in_verdict: true, scene_frame_scores: Array.from({ length: 8 }, (_, i) => ({ frame_index: i, scene_ai_prob: 0.1 })) },
    }
    render(<VideoForensicsView result={result} activeSubTab="summary" setActiveSubTab={() => {}} />)
    const row = screen.getByTestId('gend-face-score')
    expect(row).toHaveTextContent(/GenD face-swap \(in verdict\), mean \/ max over 24 faces/)
    expect(row).toHaveTextContent('82% / 97%')
  })

  it('says not applicable when GenD found no face', () => {
    const result = { ...realVideoFaceswapResult, evidence: { ...realVideoFaceswapResult.evidence, gend_face_mean: null, gend_face_max: null } }
    render(<VideoForensicsView result={result} activeSubTab="summary" setActiveSubTab={() => {}} />)
    expect(screen.getByTestId('gend-face-score')).toHaveTextContent(/No face found: not applicable/)
  })
})
