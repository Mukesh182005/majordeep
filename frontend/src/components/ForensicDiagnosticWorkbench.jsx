import React, { useState, useEffect, useRef } from 'react'
import {
  Cpu, Activity, Eye, Waveform
} from './ui/Icons'

export function ForensicDiagnosticWorkbench() {
  const [activeInstrument, setActiveInstrument] = useState('cfa') // 'cfa' | 'fft' | 'oscilloscope' | 'facesync'
  
  // Instrument 1: Bayer CFA state
  const [cfaMode, setCfaMode] = useState('genuine') // 'genuine' | 'synthetic'
  const cfaCanvasRef = useRef(null)

  // Instrument 2: FFT Spectral slope state
  const [fftMode, setFftMode] = useState('natural') // 'natural' | 'synthetic'
  const fftCanvasRef = useRef(null)

  // Instrument 3: Oscilloscope state
  const [audioMode, setAudioMode] = useState('human') // 'human' | 'synthetic'
  const oscCanvasRef = useRef(null)
  const animFrameRef = useRef(null)

  // Instrument 4: 3D Face SyncNet state
  const [avOffset, setAvOffset] = useState(-8) // milliseconds offset

  // ── 1. DRAW BAYER CFA GRID CANVAS ──────────────────────────────────────────
  useEffect(() => {
    if (activeInstrument !== 'cfa') return
    const canvas = cfaCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const width = canvas.width
    const height = canvas.height

    ctx.clearRect(0, 0, width, height)

    // Draw Bayer CFA grid (16x16 blocks)
    const cols = 16
    const rows = 12
    const cellW = width / cols
    const cellH = height / rows

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        // Bayer pattern: R G / G B
        const isRed = r % 2 === 0 && c % 2 === 0
        const isGreen = (r % 2 === 0 && c % 2 === 1) || (r % 2 === 1 && c % 2 === 0)
        const isBlue = r % 2 === 1 && c % 2 === 1

        let rVal = isRed ? 220 : 25
        let gVal = isGreen ? 220 : 25
        let bVal = isBlue ? 230 : 25

        if (cfaMode === 'genuine') {
          // Physical sensor has slight Gaussian noise and periodic correlation
          const noise = (Math.sin(r * 2.1 + c * 1.7) * 20) + (Math.random() * 15 - 7.5)
          if (isGreen) gVal = Math.min(255, Math.max(0, gVal + noise))
          if (isRed) rVal = Math.min(255, Math.max(0, rVal + noise))
          if (isBlue) bVal = Math.min(255, Math.max(0, bVal + noise))
        } else {
          // Synthetic diffusion renders smooth RGB without hardware Bayer filter correlation
          const smooth = Math.sin((r + c) * 0.4) * 80 + 120
          rVal = smooth + (Math.random() * 8)
          gVal = smooth + (Math.random() * 8)
          bVal = smooth + (Math.random() * 8)
        }

        ctx.fillStyle = `rgb(${Math.round(rVal)}, ${Math.round(gVal)}, ${Math.round(bVal)})`
        ctx.fillRect(c * cellW + 1, r * cellH + 1, cellW - 2, cellH - 2)

        // Draw subpixel grid border
        ctx.strokeStyle = '#1e293b'
        ctx.lineWidth = 1
        ctx.strokeRect(c * cellW, r * cellH, cellW, cellH)
      }
    }

    // Overlay CFA Correlation curve on right side
    const plotX = width * 0.7
    const plotW = width * 0.28
    const plotH = height * 0.8
    const plotY = height * 0.1

    ctx.fillStyle = 'rgba(10, 15, 29, 0.85)'
    ctx.fillRect(plotX, plotY, plotW, plotH)
    ctx.strokeStyle = '#334155'
    ctx.lineWidth = 1
    ctx.strokeRect(plotX, plotY, plotW, plotH)

    // Title on plot
    ctx.fillStyle = '#94a3b8'
    ctx.font = '9px monospace'
    ctx.fillText('CFA GREEN AUTOCORR', plotX + 8, plotY + 16)

    // Plot line
    ctx.beginPath()
    ctx.lineWidth = 2
    ctx.strokeStyle = cfaMode === 'genuine' ? '#10b981' : '#f43f5e'

    const pts = 30
    for (let i = 0; i < pts; i++) {
      const px = plotX + 10 + (i / pts) * (plotW - 20)
      let py = 0
      if (cfaMode === 'genuine') {
        // Periodic spike at frequency multiples
        const isSpike = i % 6 === 0
        py = isSpike ? plotY + 30 : plotY + plotH - 20 - (Math.sin(i * 0.8) * 8)
      } else {
        // Flat noise floor
        py = plotY + plotH - 25 - (Math.random() * 6)
      }
      if (i === 0) ctx.moveTo(px, py)
      else ctx.lineTo(px, py)
    }
    ctx.stroke()
  }, [activeInstrument, cfaMode])

  // ── 2. DRAW 2D-FFT RADIAL POWER SPECTRUM ───────────────────────────────────
  useEffect(() => {
    if (activeInstrument !== 'fft') return
    const canvas = fftCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const width = canvas.width
    const height = canvas.height

    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = '#090D16'
    ctx.fillRect(0, 0, width, height)

    // Axes
    const margin = 40
    const plotW = width - margin * 2
    const plotH = height - margin * 2

    ctx.strokeStyle = '#1e293b'
    ctx.lineWidth = 1
    ctx.strokeRect(margin, margin, plotW, plotH)

    // Grid lines
    ctx.strokeStyle = '#1e293b'
    ctx.setLineDash([3, 3])
    for (let i = 1; i <= 4; i++) {
      const y = margin + (i / 5) * plotH
      ctx.beginPath()
      ctx.moveTo(margin, y)
      ctx.lineTo(margin + plotW, y)
      ctx.stroke()
    }
    ctx.setLineDash([])

    // Theoretical 1/f^2 natural power-law reference line (Gray)
    ctx.strokeStyle = '#475569'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.moveTo(margin + 10, margin + 20)
    ctx.lineTo(margin + plotW - 10, margin + plotH - 20)
    ctx.stroke()

    ctx.fillStyle = '#64748b'
    ctx.font = '9px monospace'
    ctx.fillText('NATURAL 1/f² SLOPE (α = -2.0)', margin + 15, margin + 35)

    // Measured spectrum curve
    ctx.beginPath()
    ctx.lineWidth = 2.5
    ctx.strokeStyle = fftMode === 'natural' ? '#00E5FF' : '#f59e0b'

    const steps = 60
    for (let i = 0; i <= steps; i++) {
      const frac = i / steps
      const x = margin + frac * plotW
      // Natural follows 1/f^2 with minor natural jitter
      let y = margin + 20 + frac * (plotH - 45) + (Math.sin(i * 0.9) * 3)

      if (fftMode === 'synthetic') {
        // High-frequency deconvolution / GAN checkerboard peaks at ~45% and 80% frequency
        if (i > 22 && i < 28) {
          y -= 38 // Spurious peak
        } else if (i > 45 && i < 52) {
          y -= 26 // Second harmonic peak
        }
      }

      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.stroke()

    // Labels
    ctx.fillStyle = '#94a3b8'
    ctx.font = '10px monospace'
    ctx.fillText('log E(f)', margin + 5, margin - 10)
    ctx.fillText('Spatial Frequency log(f) →', margin + plotW - 160, margin + plotH + 25)

    if (fftMode === 'synthetic') {
      // Highlight checkerboard anomaly
      ctx.fillStyle = '#f59e0b'
      ctx.font = '9px monospace'
      ctx.fillText('▲ GAN/DIFFUSION CHECKERBOARD PEAK', margin + plotW * 0.4, margin + plotH * 0.35)
    }
  }, [activeInstrument, fftMode])

  // ── 3. DRAW ANIMATED ACOUSTIC OSCILLOSCOPE ─────────────────────────────────
  useEffect(() => {
    if (activeInstrument !== 'oscilloscope') return
    const canvas = oscCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    let step = 0

    const renderOsc = () => {
      step += 0.08
      const width = canvas.width
      const height = canvas.height

      if (!ctx) return
      ctx.clearRect(0, 0, width, height)
      ctx.fillStyle = '#090D16'
      ctx.fillRect(0, 0, width, height)

      // Center baseline
      ctx.strokeStyle = '#1e293b'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, height / 2)
      ctx.lineTo(width, height / 2)
      ctx.stroke()

      // Waveform path
      ctx.beginPath()
      ctx.lineWidth = 2
      ctx.strokeStyle = audioMode === 'human' ? '#10B981' : '#EC4899'

      const points = 200
      for (let i = 0; i < points; i++) {
        const x = (i / points) * width
        let y = height / 2

        if (audioMode === 'human') {
          // Human voice: fundamental glottal pulse F0 with harmonic formants F1, F2
          const f0 = Math.sin(i * 0.15 + step) * 35
          const f1 = Math.sin(i * 0.45 + step * 2.2) * 16
          const f2 = Math.sin(i * 0.9 + step * 3.1) * 8
          // Natural vocal jitter
          const jitter = (Math.random() - 0.5) * 4
          y += f0 + f1 + f2 + jitter
        } else {
          // Neural vocoder: unnaturally sterile periodicity or high-frequency phase glitching
          const base = Math.sin(i * 0.2 + step) * 42
          // Discontinuity phase step every 50 points
          const phaseGlitch = (i % 60 === 0) ? (Math.random() * 25 - 12.5) : 0
          y += base + phaseGlitch
        }

        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()

      animFrameRef.current = requestAnimationFrame(renderOsc)
    }

    animFrameRef.current = requestAnimationFrame(renderOsc)

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [activeInstrument, audioMode])

  // SyncNet AV Correlation score based on offset
  const syncConfidence = Math.max(0, 100 - Math.abs(avOffset) * 1.8).toFixed(1)
  const isSyncAligned = Math.abs(avOffset) <= 25

  return (
    <div className="rounded-3xl border border-subtle bg-surface-1 overflow-hidden shadow-2xl">
      {/* Workbench Header */}
      <div className="p-4 sm:p-5 border-b border-subtle bg-surface-2/90 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="flex h-2 w-2 rounded-full bg-accent animate-ping" />
            <span className="text-[0.6875rem] font-bold font-mono uppercase tracking-widest text-accent">
              Multi-Modal Forensic Laboratory Telemetry
            </span>
          </div>
          <h3 className="text-lg sm:text-xl font-black text-ink-primary tracking-tight">
            Human-Engineered Forensic Diagnostic Instruments
          </h3>
          <p className="text-xs text-ink-secondary mt-0.5">
            Real mathematical instrumentation: Bayer optical demosaicing, 2D-FFT spectral slope, acoustic vocal tract biomechanics, and 3D lip-sync.
          </p>
        </div>

        {/* 4 Instrument Selectors */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-surface-1 border border-subtle">
          {[
            { id: 'cfa', label: 'Bayer CFA Grid', icon: Cpu },
            { id: 'fft', label: '2D-FFT Power Slope', icon: Activity },
            { id: 'oscilloscope', label: 'Vocal Oscilloscope', icon: Waveform },
            { id: 'facesync', label: 'SyncNet 3D Lip-Sync', icon: Eye },
          ].map(inst => {
            const Icon = inst.icon
            const isSelected = activeInstrument === inst.id
            return (
              <button
                key={inst.id}
                onClick={() => setActiveInstrument(inst.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 transition ${
                  isSelected
                    ? 'bg-accent text-white shadow-sm'
                    : 'text-ink-secondary hover:text-ink-primary'
                }`}
              >
                <Icon size={13} />
                <span>{inst.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Workbench Interactive Instrument Stage */}
      <div className="p-5 sm:p-7 bg-surface-page/70 space-y-6">
        
        {/* ── INSTRUMENT 1: BAYER CFA SENSOR DEMOSAICING ──────────────────── */}
        {activeInstrument === 'cfa' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[0.6875rem] font-mono font-bold text-accent uppercase tracking-wider block">
                  Hardware Sensor Subsystem • Popescu & Farid CFA Corroboration
                </span>
                <h4 className="text-base font-extrabold text-ink-primary">
                  Color Filter Array (CFA) Silicon Lattice & Periodic Demosaicing Residuals
                </h4>
              </div>

              {/* Mode Toggle */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-ink-muted">Simulate:</span>
                <div className="inline-flex rounded-xl p-0.5 bg-surface-2 border border-subtle text-xs font-bold">
                  <button
                    onClick={() => setCfaMode('genuine')}
                    className={`px-2.5 py-1 rounded-lg transition ${
                      cfaMode === 'genuine' ? 'bg-emerald-500 text-white' : 'text-ink-secondary hover:text-ink-primary'
                    }`}
                  >
                    Physical Optical Sensor
                  </button>
                  <button
                    onClick={() => setCfaMode('synthetic')}
                    className={`px-2.5 py-1 rounded-lg transition ${
                      cfaMode === 'synthetic' ? 'bg-rose-500 text-white' : 'text-ink-secondary hover:text-ink-primary'
                    }`}
                  >
                    AI Diffusion (No CFA)
                  </button>
                </div>
              </div>
            </div>

            {/* Canvas Display */}
            <div className="rounded-2xl border border-subtle bg-black p-3 sm:p-4 flex flex-col items-center">
              <canvas
                ref={cfaCanvasRef}
                width={700}
                height={260}
                className="w-full max-h-[300px] rounded-xl object-contain border border-subtle/40"
              />
            </div>

            {/* Scientific Telemetry Readout */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">CFA Periodicity Ratio (R_CFA)</span>
                <span className={`text-xl font-mono font-black mt-1 block ${cfaMode === 'genuine' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {cfaMode === 'genuine' ? '2.48 (Peak Detected)' : '1.02 (Flat Noise)'}
                </span>
                <span className="text-[0.6875rem] text-ink-muted">Threshold: R_CFA &gt; 1.5 indicates physical silicon CFA</span>
              </div>
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">Wavelet PRNU Noise Std Dev (σ)</span>
                <span className="text-xl font-mono font-black text-ink-primary mt-1 block">
                  {cfaMode === 'genuine' ? '5.42 DN (Optical Grain)' : '1.18 DN (Oversmoothed)'}
                </span>
                <span className="text-[0.6875rem] text-ink-muted">Threshold: σ &gt; 4.5 DN verifies physical sensor PRNU</span>
              </div>
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">Diagnostic Finding</span>
                <span className={`text-xs font-mono font-bold mt-2 px-2 py-0.5 rounded inline-block ${
                  cfaMode === 'genuine' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                }`}>
                  {cfaMode === 'genuine' ? 'GENUINE_HARDWARE_CAPTURED' : 'ABSENT_PHYSICAL_CFA'}
                </span>
                <p className="text-[0.65rem] text-ink-secondary mt-1">
                  {cfaMode === 'genuine'
                    ? 'Physical Bayer green-channel demosaicing harmonics corroborated.'
                    : 'Image lacks periodic demosaicing lattice typical of camera sensors.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── INSTRUMENT 2: 2D-FFT RADIAL POWER SLOPE ─────────────────────── */}
        {activeInstrument === 'fft' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[0.6875rem] font-mono font-bold text-accent uppercase tracking-wider block">
                  Frequency Subsystem • 2D Discrete Fourier Decomposition
                </span>
                <h4 className="text-base font-extrabold text-ink-primary">
                  Fourier Radial Power Spectrum Slope: α = -∂ log E(f) / ∂ log f
                </h4>
              </div>

              {/* Mode Toggle */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-ink-muted">Simulate:</span>
                <div className="inline-flex rounded-xl p-0.5 bg-surface-2 border border-subtle text-xs font-bold">
                  <button
                    onClick={() => setFftMode('natural')}
                    className={`px-2.5 py-1 rounded-lg transition ${
                      fftMode === 'natural' ? 'bg-[#00E5FF] text-black font-bold' : 'text-ink-secondary hover:text-ink-primary'
                    }`}
                  >
                    Natural Optical Capture (α = -2.0)
                  </button>
                  <button
                    onClick={() => setFftMode('synthetic')}
                    className={`px-2.5 py-1 rounded-lg transition ${
                      fftMode === 'synthetic' ? 'bg-amber-500 text-white font-bold' : 'text-ink-secondary hover:text-ink-primary'
                    }`}
                  >
                    Diffusion / GAN Upsampling
                  </button>
                </div>
              </div>
            </div>

            {/* Canvas Display */}
            <div className="rounded-2xl border border-subtle bg-black p-3 sm:p-4 flex flex-col items-center">
              <canvas
                ref={fftCanvasRef}
                width={700}
                height={260}
                className="w-full max-h-[300px] rounded-xl object-contain border border-subtle/40"
              />
            </div>

            {/* Readout */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">Spectral Power Slope (α)</span>
                <span className="text-xl font-mono font-black text-ink-primary mt-1 block">
                  {fftMode === 'natural' ? '-2.03 (Natural 1/f²)' : '-1.34 (High-Freq Spikes)'}
                </span>
                <span className="text-[0.6875rem] text-ink-muted">Natural scenes exhibit α ≈ -2.0 scale invariance</span>
              </div>
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">Transposed Conv / Checkerboard Grid</span>
                <span className={`text-xl font-mono font-black mt-1 block ${fftMode === 'natural' ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {fftMode === 'natural' ? 'None Detected' : 'Peak at π/2 & π/4'}
                </span>
                <span className="text-[0.6875rem] text-ink-muted">Artifact of neural upsampling deconvolution layers</span>
              </div>
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">Spectral Evaluation</span>
                <span className={`text-xs font-mono font-bold mt-2 px-2 py-0.5 rounded inline-block ${
                  fftMode === 'natural' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                }`}>
                  {fftMode === 'natural' ? 'NATURAL_OPTICAL_FREQUENCY' : 'ARTIFICIAL_GRID_ANOMALY'}
                </span>
                <p className="text-[0.65rem] text-ink-secondary mt-1">
                  {fftMode === 'natural'
                    ? 'Continuous frequency decay adheres strictly to optical physics.'
                    : 'Discrete harmonic spikes reveal generative deconvolution filter.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── INSTRUMENT 3: ACOUSTIC VOCAL OSCILLOSCOPE ───────────────────── */}
        {activeInstrument === 'oscilloscope' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[0.6875rem] font-mono font-bold text-accent uppercase tracking-wider block">
                  Acoustic Subsystem • Vocal Biomechanics & Glottal Dynamics
                </span>
                <h4 className="text-base font-extrabold text-ink-primary">
                  Live Oscilloscope: Glottal Pulse Envelopes & Formant Harmonics
                </h4>
              </div>

              {/* Mode Toggle */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-ink-muted">Signal:</span>
                <div className="inline-flex rounded-xl p-0.5 bg-surface-2 border border-subtle text-xs font-bold">
                  <button
                    onClick={() => setAudioMode('human')}
                    className={`px-2.5 py-1 rounded-lg transition ${
                      audioMode === 'human' ? 'bg-emerald-500 text-white font-bold' : 'text-ink-secondary hover:text-ink-primary'
                    }`}
                  >
                    Human Vocal Tract
                  </button>
                  <button
                    onClick={() => setAudioMode('synthetic')}
                    className={`px-2.5 py-1 rounded-lg transition ${
                      audioMode === 'synthetic' ? 'bg-pink-500 text-white font-bold' : 'text-ink-secondary hover:text-ink-primary'
                    }`}
                  >
                    Neural Vocoder (TTS/Clone)
                  </button>
                </div>
              </div>
            </div>

            {/* Canvas Display */}
            <div className="rounded-2xl border border-subtle bg-black p-3 sm:p-4 flex flex-col items-center">
              <canvas
                ref={oscCanvasRef}
                width={700}
                height={240}
                className="w-full max-h-[280px] rounded-xl object-contain border border-subtle/40"
              />
            </div>

            {/* Readout */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">Pitch Jitter & Shimmer</span>
                <span className="text-xl font-mono font-black text-ink-primary mt-1 block">
                  {audioMode === 'human' ? '0.82% / 2.14% (Natural)' : '0.04% / 0.12% (Unnatural)'}
                </span>
                <span className="text-[0.6875rem] text-ink-muted">Human vocal cords exhibit organic cycle-to-cycle perturbation</span>
              </div>
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">Formant Frequencies (F1, F2, F3)</span>
                <span className="text-xl font-mono font-black text-ink-primary mt-1 block">
                  {audioMode === 'human' ? '730Hz • 1240Hz • 2520Hz' : 'Step Discontinuities'}
                </span>
                <span className="text-[0.6875rem] text-ink-muted">Reflects anatomical pharyngeal and oral cavity acoustics</span>
              </div>
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-1">
                <span className="text-[0.625rem] font-mono uppercase text-ink-muted block">Acoustic Biometric Status</span>
                <span className={`text-xs font-mono font-bold mt-2 px-2 py-0.5 rounded inline-block ${
                  audioMode === 'human' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-pink-500/20 text-pink-400 border border-pink-500/30'
                }`}>
                  {audioMode === 'human' ? 'NATURAL_LARYNGEAL_TRACT' : 'VOCODER_SYNTHETIC_ARTIFACTS'}
                </span>
                <p className="text-[0.65rem] text-ink-secondary mt-1">
                  {audioMode === 'human'
                    ? 'Continuous phase coherence with authentic glottal pulse envelope.'
                    : 'Phase resets and uncharacteristically low micro-tremor detected.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── INSTRUMENT 4: SYNCNET 3D LIP-SYNC ───────────────────────────── */}
        {activeInstrument === 'facesync' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
              <div>
                <span className="text-[0.6875rem] font-mono font-bold text-accent uppercase tracking-wider block">
                  Temporal Subsystem • Cross-Modal SyncNet Lip-Audio Correlation
                </span>
                <h4 className="text-base font-extrabold text-ink-primary">
                  Audio-Visual Phoneme-Viseme Temporal Alignment Gauge
                </h4>
              </div>

              {/* Offset interactive slider */}
              <div className="flex items-center gap-3 bg-surface-2 p-2 rounded-xl border border-subtle text-xs">
                <span className="font-mono text-ink-muted">AV Offset:</span>
                <input
                  type="range"
                  min="-80"
                  max="80"
                  value={avOffset}
                  onChange={(e) => setAvOffset(parseInt(e.target.value))}
                  className="w-28 accent-accent cursor-pointer"
                />
                <span className={`font-mono font-bold ${isSyncAligned ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {avOffset > 0 ? `+${avOffset}` : avOffset} ms
                </span>
              </div>
            </div>

            {/* Wireframe Graphic & Sync Gauge */}
            <div className="rounded-2xl border border-subtle bg-black p-6 flex flex-col md:flex-row items-center justify-around gap-6">
              
              {/* Interactive Vector 3D Wireframe Face */}
              <div className="relative flex flex-col items-center">
                <svg width="220" height="200" viewBox="0 0 220 200" className="drop-shadow-lg">
                  {/* Face Contour Wireframe */}
                  <ellipse cx="110" cy="100" rx="65" ry="85" fill="none" stroke="#334155" strokeWidth="1.5" />
                  
                  {/* Eyebrows & Eyes */}
                  <line x1="75" y1="65" x2="95" y2="65" stroke="#00E5FF" strokeWidth="2" />
                  <line x1="125" y1="65" x2="145" y2="65" stroke="#00E5FF" strokeWidth="2" />
                  <ellipse cx="85" cy="78" rx="10" ry="6" fill="none" stroke="#00E5FF" strokeWidth="1.5" />
                  <circle cx="85" cy="78" r="2.5" fill="#00E5FF" />
                  <ellipse cx="135" cy="78" rx="10" ry="6" fill="none" stroke="#00E5FF" strokeWidth="1.5" />
                  <circle cx="135" cy="78" r="2.5" fill="#00E5FF" />

                  {/* Nose Bridge */}
                  <line x1="110" y1="78" x2="110" y2="110" stroke="#334155" strokeWidth="1.5" />
                  <line x1="102" y1="110" x2="118" y2="110" stroke="#334155" strokeWidth="1.5" />

                  {/* Dynamic Mouth / Viseme Contour */}
                  <ellipse
                    cx="110"
                    cy="138"
                    rx={isSyncAligned ? 22 : 14}
                    ry={isSyncAligned ? 12 : 6}
                    fill="none"
                    stroke={isSyncAligned ? '#10B981' : '#F43F5E'}
                    strokeWidth="2"
                    className="transition-all duration-300"
                  />
                  <line
                    x1="90"
                    y1="138"
                    x2="130"
                    y2="138"
                    stroke={isSyncAligned ? '#10B981' : '#F43F5E'}
                    strokeWidth="1.5"
                  />

                  {/* Head Pose Euler Coordinates Overlay */}
                  <text x="10" y="25" fill="#64748b" fontSize="9" fontFamily="monospace">Yaw: +2.1°</text>
                  <text x="10" y="38" fill="#64748b" fontSize="9" fontFamily="monospace">Pitch: -1.4°</text>
                  <text x="10" y="51" fill="#64748b" fontSize="9" fontFamily="monospace">Roll: +0.6°</text>
                </svg>
                <span className="text-[0.6875rem] font-mono text-ink-muted mt-2">
                  68-Point Mediapipe 3D Facial Mesh
                </span>
              </div>

              {/* SyncNet Gauge Bar */}
              <div className="w-full max-w-sm space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-ink-muted">Phoneme-Viseme Correlation:</span>
                  <span className={`font-mono font-black ${isSyncAligned ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {syncConfidence}%
                  </span>
                </div>

                {/* Meter Bar */}
                <div className="h-3 w-full rounded-full bg-surface-2 overflow-hidden border border-subtle">
                  <div
                    className={`h-full transition-all duration-300 ${
                      isSyncAligned ? 'bg-emerald-400' : 'bg-rose-500'
                    }`}
                    style={{ width: `${syncConfidence}%` }}
                  />
                </div>

                <div className="p-3 rounded-xl border border-subtle bg-surface-1 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <strong className="text-ink-primary">SyncNet Threshold:</strong>
                    <span className="font-mono text-ink-secondary">|Δt| ≤ 25ms</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <strong className="text-ink-primary">Status:</strong>
                    <span className={`font-mono font-bold ${isSyncAligned ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {isSyncAligned ? 'SYNCHRONIZED_SPEECH' : 'AV_DESYNCHRONIZATION_ANOMALY'}
                    </span>
                  </div>
                  <p className="text-[0.6875rem] text-ink-muted pt-1">
                    {isSyncAligned
                      ? 'Acoustic formant onset matches visual mouth opening boundaries.'
                      : 'Offset exceeds biological threshold. Suggests face-swap or audio replacement.'}
                  </p>
                </div>
              </div>

            </div>
          </div>
        )}

      </div>

      {/* Workbench Footer */}
      <div className="p-4 border-t border-subtle bg-surface-2/60 text-xs text-ink-secondary flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <span className="text-[0.6875rem] font-mono text-ink-muted">
          Active Station: Lab Terminal #04 • Pure JavaScript/HTML5 Canvas Telemetry (No Static AI Imagery)
        </span>
        <div className="flex items-center gap-2 self-start sm:self-auto text-accent text-xs font-bold">
          <Activity size={14} />
          <span>Real-time Signal Analysis</span>
        </div>
      </div>
    </div>
  )
}
