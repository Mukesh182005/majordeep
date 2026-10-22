import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Result from '../Result'
import realAudioResult from '../../components/__tests__/fixtures/real_audio_result.json'

const mockVideoResult = {
  id: 'job-vid-999',
  case_reference: 'CASE-VID-999',
  status: 'done',
  media_type: 'video',
  original_filename: 'test_video.mp4',
  sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  file_size_bytes: 4096000,
  verdict: 'MANIPULATED',
  fake_probability: 0.82,
  confidence: 0.95,
  evidence: {
    media: 'video',
    dominant_threat: 'Synthetic Face Swap & Diffusion',
    threat_code: 'FACE_SWAP',
    processing_ms: 850,
    pipeline_modules: [
      { stage: 1, name: 'Container & Bitstream Forensics', status: 'PASSED', duration_ms: 10, desc: 'Container valid' },
      { stage: 2, name: 'Scene & Shot Boundary Segmentation', status: 'PASSED', duration_ms: 20, desc: '1 scene' },
      { stage: 3, name: 'Spatial Neural & Generative AI Backbone', status: 'AI_FLAGGED', duration_ms: 100, desc: 'AI detected' },
    ],
  },
}

vi.mock('../../lib/api', () => ({
  api: {
    reportUrl: vi.fn((id) => `/api/v1/jobs/${id}/report.pdf`),
  },
  connectJobWs: vi.fn((jobId) => {
    if (jobId === 'job-audio-real-1') {
      return Promise.resolve(realAudioResult)
    }
    return Promise.resolve(mockVideoResult)
  }),
}))

describe('Result page video pipeline rendering', () => {
  it('renders Pipeline Stages in top tabs and pipeline preview card in Analysis tab', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-vid-999']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    // Wait for mock job data to resolve
    await waitFor(() => {
      expect(screen.getByText('Pipeline Stages')).toBeInTheDocument()
    })

    // Check preview card on analysis tab
    expect(screen.getByText(/Forensic Pipeline Execution/i)).toBeInTheDocument()

    // Click top tab "Pipeline Stages"
    const pipelineTab = screen.getByText('Pipeline Stages')
    fireEvent.click(pipelineTab)

    // Verify full pipeline audit view appears
    await waitFor(() => {
      expect(screen.getByText(/11-Stage Multi-Modal Pipeline Architecture/i)).toBeInTheDocument()
      expect(screen.getByText(/Stage Execution Latency Waterfall/i)).toBeInTheDocument()
      expect(screen.getByText(/Multi-Disciplinary Forensic Risk Radar/i)).toBeInTheDocument()
    })
  })

  it('renders audio result page for real ml/audio-wire response with trained model score and per-window timeline', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-audio-real-1']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    // Wait for mock job data to resolve
    await waitFor(() => {
      expect(screen.getByText('Forensics')).toBeInTheDocument()
    })

    // Click Forensics tab to view AudioForensicsView
    const forensicsTab = screen.getByText('Forensics')
    fireEvent.click(forensicsTab)

    // Verify trained model score & verdict are displayed as main result
    await waitFor(() => {
      expect(screen.getByText('Trained Model Score & Verdict')).toBeInTheDocument()
      expect(screen.getByText('Per-Window Timeline (Trained Model)')).toBeInTheDocument()
      expect(screen.getByText('Supporting signals (unvalidated)')).toBeInTheDocument()
    })

    // Verify unvalidated badges on supporting signals
    expect(screen.getAllByText('Unvalidated Heuristic').length).toBe(3)

    // Verify absence of typology and generator-family panels
    expect(screen.queryByText(/typology/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/generator family/i)).not.toBeInTheDocument()
  })
})
