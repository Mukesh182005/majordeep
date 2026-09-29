import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PipelineAuditVisualizer from '../PipelineAuditVisualizer'

const mockImageResult = {
  id: 'job-img-123',
  verdict: 'AI_GENERATED',
  fake_probability: 0.82,
  evidence: {
    dominant_threat: 'Generative ViT Synthesis',
    pipeline_modules: [
      { stage: 1, name: 'Secure Ingestion & Validation', status: 'PASSED', duration_ms: 120, summary: 'JPEG valid' },
      { stage: 2, name: 'File Container & Cryptographic Ledger', status: 'PASSED', duration_ms: 300, summary: 'SHA-256 clean' },
      { stage: 3, name: 'Metadata & Digital Timeline Forensics', status: 'PASSED', duration_ms: 10, summary: 'Clean EXIF' },
      { stage: 4, name: 'Frequency & Signal Forensics (FFT / DCT / ELA)', status: 'AI_FLAGGED', duration_ms: 1500, summary: 'CFA missing' },
      { stage: 5, name: 'Tampering & Watermark Engine', status: 'PASSED', duration_ms: 2000, summary: 'No splicing' },
      { stage: 6, name: 'AI & Deepfake Detection Engine', status: 'AI_FLAGGED', duration_ms: 320, summary: 'ViT 82%' },
      { stage: 7, name: 'Steganography & Provenance Authentication', status: 'PASSED', duration_ms: 130, summary: 'Stego clear' },
      { stage: 8, name: 'Evidence Fusion & Calibrated Risk Engine', status: 'CONSENSUS_REACHED', duration_ms: 1400, summary: 'Consensus 82%' },
    ],
  },
}

describe('PipelineAuditVisualizer (Image Pipeline)', () => {
  it('renders 8-stage image modular pipeline with phases, charts, and audit trail', () => {
    render(<PipelineAuditVisualizer result={mockImageResult} pipelineModules={mockImageResult.evidence.pipeline_modules} />)

    expect(screen.getByText(/8-Stage Modular Forensic Pipeline Diagram/i)).toBeInTheDocument()
    expect(screen.getByText(/Stage Latency Waterfall/i)).toBeInTheDocument()
    expect(screen.getByText(/Visual Forensic Risk Radar/i)).toBeInTheDocument()
    expect(screen.getByText(/Linear Forensic Audit Trail/i)).toBeInTheDocument()
  })

  it('allows clicking an image stage node to select it in the deep inspector', () => {
    render(<PipelineAuditVisualizer result={mockImageResult} pipelineModules={mockImageResult.evidence.pipeline_modules} />)

    // Stage 4 node
    const stage4Button = screen.getByRole('button', { name: /Stage 4:/i })
    fireEvent.click(stage4Button)

    expect(screen.getByText(/Stage 4: Frequency & Signal Forensics \(FFT \/ DCT \/ ELA\)/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Image Forensics/i).length).toBeGreaterThanOrEqual(1)
  })

  it('triggers onSelectPlate when inspecting deep forensic plate in visual lab', () => {
    const handleSelectPlate = vi.fn()
    render(
      <PipelineAuditVisualizer
        result={mockImageResult}
        pipelineModules={mockImageResult.evidence.pipeline_modules}
        onSelectPlate={handleSelectPlate}
      />
    )

    // Stage 4 node has targetPlate 'ela'
    const stage4Button = screen.getByRole('button', { name: /Stage 4:/i })
    fireEvent.click(stage4Button)

    const plateBtn = screen.getByRole('button', { name: /Inspect in Visual Forensics Lab/i })
    fireEvent.click(plateBtn)

    expect(handleSelectPlate).toHaveBeenCalledWith('ela')
  })
})
