import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import VerdictBasis from '../VerdictBasis'

describe('VerdictBasis', () => {
  it('explains a learned-combination verdict and lists each detector score', () => {
    render(<VerdictBasis evidence={{
      verdict_basis: 'learned_combination',
      scene_model_scores: { 'SwinV2 (haywoodsloan)': 0.12, 'Community Forensics': 0.34 },
    }} />)
    expect(screen.getByText(/learned combination of the AI-generation detectors/i)).toBeInTheDocument()
    expect(screen.getByText('12.0%')).toBeInTheDocument()
    expect(screen.getByText('34.0%')).toBeInTheDocument()
    expect(screen.queryByText(/detectors disagree/i)).not.toBeInTheDocument()
  })

  it('warns when one detector is sure of AI and another sure of real (same rule as the pipeline)', () => {
    render(<VerdictBasis evidence={{ verdict_basis: 'detector_score', scene_model_scores: { A: 0.95, B: 0.04 } }} />)
    expect(screen.getByText(/The detectors disagree/i)).toBeInTheDocument()
  })

  it('shows the pipeline notes and renders nothing when there is nothing to explain', () => {
    const { container, rerender } = render(<VerdictBasis evidence={{}} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<VerdictBasis evidence={{ notes: ['No camera metadata was found.'] }} />)
    expect(screen.getByText('No camera metadata was found.')).toBeInTheDocument()
  })
})
