import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Result from '../Result'
import * as apiModule from '../../lib/api'

// Mock API with WhatsApp photograph payload (e6ce9b117fbb441b90e4792010fc90b4 telemetry)
vi.mock('../../lib/api', () => ({
  api: {
    reportUrl: vi.fn((id) => `/api/v1/jobs/${id}/report.pdf`),
    evidenceUrl: vi.fn((path) => path),
  },
  connectJobWs: vi.fn((jobId) => {
    if (jobId === 'job-inconclusive') {
      return Promise.resolve({
        id: 'job-inconclusive',
        case_reference: 'CASE-2026-INCONCL',
        status: 'done',
        media_type: 'image',
        original_filename: 'WhatsApp Image 2026-09-16.jpeg',
        sha256: '6cfd26a4e6639809958cc6c203e839fdcca021e8a91fb19b1cd0b82bd13b3afd',
        file_size_bytes: 311353,
        verdict: 'INCONCLUSIVE',
        fake_probability: 0.7963,
        confidence: 0.5926,
        evidence: {
          media: 'image',
          image_size: [1070, 852],
          faces_detected: 1,
          dominant_threat: 'Synthetic AI Generation',
          threat_code: 'SYNTHETIC_AI_GENERATION',
          ai_breakdown: {
            generative_ai_prob: 0.7963,
            face_deepfake_prob: 0.0,
            authentic_prob: 0.2037,
          },
          forensics: {
            updated_ai_scores: {
              scene_ai_prob: 0.7963,
              face_fake_prob: 0.0,
              ensemble_fake_prob: 0.7963,
            },
            camera_stats: {
              estimated_camera_family: 'Resampled / Compressed Web Media',
              cfa_periodicity_ratio: 1.81,
              sensor_noise_std: 6.916,
              sensor_noise_variance: 47.8,
            },
            metadata_forensics: {
              exif_present: false,
              timeline_consistency: 'PURGED_METADATA',
            },
            file_security: {
              format: 'JPEG',
              trailing_data_detected: true,
              trailing_bytes_count: 20,
            },
            risk_engine: {
              overall_risk_score: 80,
              risk_tier: 'HIGH_RISK',
              evidence_fusion: {
                fusion_verdict: 'ISOLATED_ANOMALY',
                orthogonal_signals_count: 1,
                corroborating_signals: ['AI Generative Pattern (ViT / Diffusion Probe: 79.6%)'],
              },
            },
          },
          mopci: {
            provenance: {
              c2pa_present: false,
              manifest_status: 'Not Detected',
            },
            generation_attribution: {
              likely_origin: 'AI-generated',
              generator_family: 'Undetermined (Statistical Detection)',
              confidence: 0.8,
            },
            source_discovery: {
              status: 'NOT_AVAILABLE',
              candidates: [],
            },
          },
        },
      })
    }

    // Default clean authentic job
    return Promise.resolve({
      id: 'job-clean-auth',
      case_reference: 'CASE-2026-CLEAN',
      status: 'done',
      media_type: 'image',
      original_filename: 'camera_raw_dslr.jpeg',
      sha256: 'a1b2c3d4e5f6',
      file_size_bytes: 2500000,
      verdict: 'AUTHENTIC',
      fake_probability: 0.04,
      confidence: 0.92,
      evidence: {
        media: 'image',
        image_size: [3000, 2000],
        faces_detected: 0,
        ai_breakdown: { generative_ai_prob: 0.04, face_deepfake_prob: 0.0, authentic_prob: 0.96 },
        forensics: {
          updated_ai_scores: { scene_ai_prob: 0.04, face_fake_prob: 0.0, ensemble_fake_prob: 0.04 },
          camera_stats: { cfa_periodicity_ratio: 2.1, sensor_noise_std: 8.4, estimated_camera_family: 'Canon EOS' },
          metadata_forensics: { exif_present: true, timeline_consistency: 'CONSISTENT' },
          file_security: { format: 'JPEG', trailing_data_detected: false },
          risk_engine: {
            overall_risk_score: 12,
            evidence_fusion: { orthogonal_signals_count: 0, corroborating_signals: [] },
          },
        },
      },
    })
  }),
}))

describe('Phase 31.6 Forensic Result UI Redesign & Evidentiary Parity', () => {
  it('renders Level 1 Forensic Assessment with INCONCLUSIVE verdict and honest blurb', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-inconclusive']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('INCONCLUSIVE')).toBeInTheDocument()
    })

    // Check that Level 1 header is present
    expect(screen.getByText(/Level 1 Forensic Assessment/i)).toBeInTheDocument()

    // Check honest blurb
    expect(screen.getByText(/Available evidence does not support a sufficiently reliable AI-generation or manipulation determination/i)).toBeInTheDocument()
  })

  it('separates raw model signals from final forensic assessment (Mandatory Distinction)', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-inconclusive']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Section B/i)).toBeInTheDocument()
    })

    // Ensure Section B title and disclaimer are rendered
    expect(screen.getByText(/Individual Model & Detector Signals/i)).toBeInTheDocument()
    expect(screen.getByText(/Mandatory Forensic Distinction/i)).toBeInTheDocument()
    expect(screen.getByText(/equivalent to the final system assessment/i)).toBeInTheDocument()

    // Model score is displayed as raw model score, not final probability
    expect(screen.getByText(/Raw model score/i)).toBeInTheDocument()
  })

  it('displays Corroboration-First panel and signals discrepancy / limited corroboration', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-inconclusive']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Evidence Corroboration & Signal Consensus/i)).toBeInTheDocument()
    })

    // Expect Limited Corroboration banner
    expect(screen.getByText(/Limited Corroboration Detected/i)).toBeInTheDocument()
    expect(screen.getByText(/Conflicting Forensic Signals Observed/i)).toBeInTheDocument()

    // Conflicting physical signals listed. CFA periodicity is not one: 96% of
    // AI images have a ratio >= 1.5, so it cannot contradict a detection.
    expect(screen.queryByText(/Physical Bayer CFA Periodicity/i)).toBeNull()
    expect(screen.getAllByText(/Sensor Noise Residual/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Social-Media Recompression/i).length).toBeGreaterThan(0)
  })

  it('treats missing metadata and social-media compression as reliability context rather than manipulation', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-inconclusive']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Input Quality & Processing Conditions/i)).toBeInTheDocument()
    })

    // WhatsApp safe UX notice
    expect(screen.getByText(/Source \/ Processing Condition Notice/i)).toBeInTheDocument()
    expect(screen.getByText(/Metadata unavailable limits provenance tracking, but does/i)).toBeInTheDocument()
    expect(screen.queryByText(/THREAT DETECTED/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/DEFINITELY FAKE/i)).not.toBeInTheDocument()
  })

  it('decouples provenance from model score: origin is Inconclusive, not AI-generated', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-inconclusive']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Provenance & Origin Status/i)).toBeInTheDocument()
    })

    // Decoupled provenance: ORIGIN INCONCLUSIVE
    const originBadges = screen.getAllByText('ORIGIN INCONCLUSIVE')
    expect(originBadges.length).toBeGreaterThan(0)

    // C2PA disclaimer
    expect(screen.getByText(/Absence of Content Credentials \(C2PA\) does not establish that the media was AI-generated/i)).toBeInTheDocument()
  })

  it('renders "Why This Result?" structured evidence and "What This Result Does Not Establish"', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-inconclusive']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Why This Result\?/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/\[Detector\]/i)).toBeInTheDocument()
    expect(screen.getByText(/\[Signal Analysis\]/i)).toBeInTheDocument()
    expect(screen.getByText(/\[Metadata\]/i)).toBeInTheDocument()
    expect(screen.getByText(/\[Provenance\]/i)).toBeInTheDocument()
    expect(screen.getByText(/\[Decision Policy\]/i)).toBeInTheDocument()

    // Negative disclaimers
    expect(screen.getByText(/What This Result Does Not Establish/i)).toBeInTheDocument()
    expect(screen.getByText(/It does not establish who created or transmitted the media/i)).toBeInTheDocument()
    expect(screen.getByText(/It does not establish malicious intent or fraudulent purpose/i)).toBeInTheDocument()
  })

  it('renders Forensic Evidence Matrix with genuine backend measurements', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-inconclusive']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<Result />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Forensic Evidence Matrix/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/Camera Sensor CFA Periodicity/i)).toBeInTheDocument()
    expect(screen.getByText(/1.81 ratio/i)).toBeInTheDocument()
    expect(screen.getByText(/6.92 std/i)).toBeInTheDocument()
  })
})
