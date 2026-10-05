import React from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import HowItWorks from '../HowItWorks'

describe('HowItWorks Page Rendering', () => {
  it('renders without throwing error', () => {
    render(
      <MemoryRouter>
        <HowItWorks />
      </MemoryRouter>
    )
    expect(screen.getByText(/Veritas Multi-Modal Forensic Engine/i)).toBeInTheDocument()
  })
})
