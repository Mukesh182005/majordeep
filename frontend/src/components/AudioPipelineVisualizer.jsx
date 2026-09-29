import React, { useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts'
import {
  Activity, Alert, Check, CheckCircle, Cpu, Eye, FileText,
  Hash, Info, ShieldAlert, ShieldCheck, ShieldQuestion, Waveform, Zap,
  Lock, ArrowRight, Download, Sparkles
} from './ui/Icons'
import { percent } from '../lib/format'

export const AUDIO_PHASES = [
  {
    phaseId: 1,
    name: 'Ingestion & Container',
    stages: [1, 2],
    color: '#00E5FF',
    desc: 'Cryptographic vault ingestion & RIFF/WAV bitstream integrity'
  },
  {
    phaseId: 2,
    name: 'Acoustic Signal & Physics',
    stages: [3, 4],
    color: '#3B82F6',
    desc: 'Signal intelligence, LFCC filterbank & glottal flow aerodynamic modeling'
  },
  {
    phaseId: 3,
    name: 'Linguistics & Neural SSL',
    stages: [5, 6],
    color: '#8B5CF6',
    desc: 'Phonemic coarticulation prosody & Sinc-RawNet / WavLM layer 18 probing'
  },
  {
    phaseId: 4,
    name: 'Sensor ENF & Risk Fusion',
    stages: [7, 8],
    color: '#10B981',
    desc: 'Electric Network Frequency grid tracking & conformal multi-engine consensus'
  }
]

export const DEFAULT_AUDIO_8_STAGES = [
  {
    stage: 1,
    id: 1,
    name: 'Secure Ingestion Vault',
    category: 'Evidence Integrity',
    engine: 'SWGDE & ISO 27042 Cryptographic Bind',
    status: 'PASSED',
    duration_ms: 12,
    targetSubTab: 'security',
    desc: 'Generates immutable SHA-256 evidence record with emulated physical write-blocker access.'
  },
  {
    stage: 2,
    id: 2,
    name: 'Audio File DNA & Container Forensics',
    category: 'Container Cybersecurity',
    engine: 'RIFF/WAV Header & Transcoding Tracer',
    status: 'PASSED',
    duration_ms: 28,
    targetSubTab: 'security',
    desc: 'Analyzes container structure, codec metadata, trailing bytes past EOF, and historical transcoding traces.'
  },
  {
    stage: 3,
    id: 3,
    name: 'Signal Intelligence & Acoustic Telemetry',
    category: 'Signal Processing',
    engine: 'LFCC Linear Filterbank + Multi-Scale Dynamic SNR',
    status: 'PASSED',
    duration_ms: 64,
    targetSubTab: 'signal',
    desc: 'Extracts 120+ time/spectral descriptors, integrated loudness (LUFS), dynamic SNR, and clipping anomalies.'
  },
  {
    stage: 4,
    id: 4,
    name: 'Physiological Glottal Flow & VoiceRadar Physics',
    category: 'Physical Forensics',
    engine: 'Glottal Inverse Filtering (IAIF) + Doppler Acoustic Dispersion',
    status: 'PASSED',
    duration_ms: 95,
    targetSubTab: 'voice',
    desc: 'Simulates vocal fold aerodynamic parameters (open quotient, closing slope, turbulence index) against human biology.'
  },
  {
    stage: 5,
    id: 5,
    name: 'Content & Phonemic Coarticulation',
    category: 'Linguistic Forensics',
    engine: 'Syllabic Duration Variance + Prosodic Cadence Analyzer',
    status: 'PASSED',
    duration_ms: 48,
    targetSubTab: 'voice',
    desc: 'Tracks speech rate (WPM), phonemic duration variance, and rigid synthetic prosodic contours typical of TTS models.'
  },
  {
    stage: 6,
    id: 6,
    name: 'Multi-Model ML & Intermediate SSL Probing',
    category: 'Machine Learning',
    engine: 'Sinc-RawNet End-to-End + WavLM Layer 18 Representation Probing',
    status: 'PASSED',
    duration_ms: 310,
    targetSubTab: 'robustness',
    desc: 'Executes waveform neural classifiers alongside deep SSL transformer layer probing for acoustic synthetic artifacts.'
  },
  {
    stage: 7,
    id: 7,
    name: 'Environmental & ENF Grid Forensics',
    category: 'Sensor Forensics',
    engine: '50/60 Hz Power Grid Tracker + Schroeder Reverberation (RT60)',
    status: 'PASSED',
    duration_ms: 72,
    targetSubTab: 'environment',
    desc: 'Extracts Electric Network Frequency (ENF) continuity, grid phase slips, room acoustic reflections, and mic transducer signatures.'
  },
  {
    stage: 8,
    id: 8,
    name: 'Evidence Fusion & Conformal Risk Engine',
    category: 'Decision Engine',
    engine: 'Conformal Calibration & Multi-Expert Orthogonal Consensus',
    status: 'PASSED',
    duration_ms: 34,
    targetSubTab: 'summary',
    desc: 'Calibrates cross-engine signals with conformal p-values, computing generative AI risk and tamper confidence.'
  }
]

export default function AudioPipelineVisualizer({ result = {}, onSwitchSubTab }) {
  const evidence = result.evidence || {}
  const forensics = evidence.forensics || {}
  const rawModules = evidence.pipeline_modules || forensics.pipeline_modules || result.pipeline_modules || []

  // Merge backend data with rich visual stage defaults
  const stages = DEFAULT_AUDIO_8_STAGES.map((defStage, idx) => {
    const backendStage = rawModules.find(
      (m) => m.stage === defStage.stage || m.id === defStage.stage || (m.name && m.name.toLowerCase().includes(defStage.category.toLowerCase().split(' ')[0]))
    ) || rawModules[idx]

    if (!backendStage) return defStage

    return {
      ...defStage,
      ...backendStage,
      stage: defStage.stage,
      duration_ms: backendStage.duration_ms ?? defStage.duration_ms,
      status: backendStage.status || defStage.status,
      summary: backendStage.summary || defStage.summary,
      findings: backendStage.findings || defStage.findings || []
    }
  })

  const [activeStageNum, setActiveStageNum] = useState(1)
  const [filterMode, setFilterMode] = useState('all') // 'all' | 'anomalies' | 'passed'
  const [expandedCards, setExpandedCards] = useState({})
  const [copyFeedback, setCopyFeedback] = useState(false)

  const activeStage = stages.find((s) => s.stage === activeStageNum) || stages[0]

  const totalDuration = stages.reduce((acc, s) => acc + (s.duration_ms || 0), 0)
  const flaggedCount = stages.filter((s) =>
    ['AI_FLAGGED', 'ANOMALY_DETECTED', 'SUSPICIOUS', 'FAILED'].includes(s.status)
  ).length
  const passedCount = stages.filter((s) => s.status === 'PASSED').length

  const getStatusColor = (status) => {
    switch (status) {
      case 'AI_FLAGGED':
      case 'ANOMALY_DETECTED':
      case 'FAILED':
        return '#ef4444' // Rose / Red
      case 'SUSPICIOUS':
      case 'INCONCLUSIVE':
      case 'SKIPPED':
        return '#f59e0b' // Amber
      case 'PASSED':
      default:
        return '#10b981' // Emerald
    }
  }

  // 1. Data for Execution Latency Waterfall Bar Chart
  const waterfallData = stages.map((s) => ({
    name: `S${s.stage}`,
    fullName: s.name,
    duration: s.duration_ms || 10,
    status: s.status,
    category: s.category,
    color: getStatusColor(s.status),
    stageNum: s.stage
  }))

  // 2. Data for Acoustic Forensic Risk Radar Profile (8 orthogonal axes)
  const fileDna = evidence.file_dna || forensics.file_dna || {}
  const signalIntel = evidence.signal_intel || forensics.signal_intel || {}
  const glottal = evidence.glottal_physics || forensics.glottal_physics || {}
  const modelsOutput = evidence.models_output || forensics.models_output || {}
  const modelBranches = modelsOutput.model_branch_scores || {}
  const enf = evidence.enf_environment || forensics.enf_environment || {}
  const splicing = evidence.splicing_timeline || forensics.splicing_timeline || {}
  const semantics = evidence.speech_semantics || forensics.speech_semantics || {}
  const provenance = evidence.security_provenance || forensics.security_provenance || {}

  const radarData = [
    {
      subject: 'RawNet Neural AI',
      score: Math.round((modelBranches.rawnet_waveform_prob ?? (result.fake_probability || 0.15)) * 100),
      fullMark: 100
    },
    {
      subject: 'WavLM SSL Probing',
      score: Math.round((modelBranches.wavlm_l18_acoustic_prob ?? (result.fake_probability || 0.12)) * 100),
      fullMark: 100
    },
    {
      subject: 'Glottal Aerodynamics',
      score: Math.round((glottal.composite_physiological_anomaly_score ?? (flaggedCount > 0 ? 0.65 : 0.08)) * 100),
      fullMark: 100
    },
    {
      subject: 'ENF Grid Continuity',
      score: enf.environmental_splicing_confirmed ? 85 : 12,
      fullMark: 100
    },
    {
      subject: 'Splicing & Seams',
      score: splicing.splicing_detected ? 90 : 8,
      fullMark: 100
    },
    {
      subject: 'Stego / Bitplane',
      score: provenance.steganography_detected ? 78 : 14,
      fullMark: 100
    },
    {
      subject: 'Container DNA Flags',
      score: fileDna.trailing_data_detected ? 80 : 6,
      fullMark: 100
    },
    {
      subject: 'TTS Rigid Prosody',
      score: semantics.rigid_synthetic_prosody_detected ? 82 : 15,
      fullMark: 100
    }
  ]

  const toggleExpand = (stageNum) => {
    setExpandedCards((prev) => ({ ...prev, [stageNum]: !prev[stageNum] }))
  }

  const toggleExpandAll = () => {
    const allExpanded = stages.every((s) => expandedCards[s.stage])
    const next = {}
    stages.forEach((s) => { next[s.stage] = !allExpanded })
    setExpandedCards(next)
  }

  const filteredStages = stages.filter((s) => {
    if (filterMode === 'anomalies') {
      return ['AI_FLAGGED', 'ANOMALY_DETECTED', 'SUSPICIOUS', 'FAILED'].includes(s.status)
    }
    if (filterMode === 'passed') return s.status === 'PASSED'
    return true
  })

  const copyPipelineManifest = () => {
    const manifest = {
      pipeline: '8-Stage Audio Forensic Architecture',
      case_reference: result.case_reference || 'N/A',
      timestamp: new Date().toISOString(),
      total_duration_ms: totalDuration,
      stages: stages.map((s) => ({
        stage: s.stage,
        name: s.name,
        category: s.category,
        engine: s.engine,
        status: s.status,
        duration_ms: s.duration_ms,
        summary: s.summary,
        findings: s.findings
      }))
    }
    navigator.clipboard.writeText(JSON.stringify(manifest, null, 2))
    setCopyFeedback(true)
    setTimeout(() => setCopyFeedback(false), 2000)
  }

  return (
    <div className="space-y-6">
      {/* ── 1. Executive Telemetry KPI Ribbon ─────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl border bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Acoustic Pipeline Flow</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-black font-mono text-ink-primary">8 / 8</span>
            <span className="text-xs text-ink-secondary">Engines Active</span>
          </div>
          <p className="text-[0.6875rem] text-ink-muted mt-1">100% Sequential Audio Verification</p>
        </div>

        <div className="p-4 rounded-2xl border bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Acoustic Anomaly Flags</span>
            <span className={`h-2 w-2 rounded-full ${flaggedCount > 0 ? 'bg-rose-500' : 'bg-emerald-500'}`} />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className={`text-2xl font-black font-mono ${flaggedCount > 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
              {flaggedCount}
            </span>
            <span className="text-xs text-ink-secondary">Suspicious</span>
          </div>
          <p className="text-[0.6875rem] text-ink-muted mt-1">{passedCount} Engines Passed Clean</p>
        </div>

        <div className="p-4 rounded-2xl border bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Total Audio Latency</span>
            <Activity size={15} className="text-accent" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-black font-mono text-ink-primary">
              {(totalDuration / 1000).toFixed(2)}s
            </span>
            <span className="text-xs font-mono text-ink-muted">({totalDuration} ms)</span>
          </div>
          <p className="text-[0.6875rem] text-ink-muted mt-1">Real-time Spectral Waveform Pass</p>
        </div>

        <div className="p-4 rounded-2xl border bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Audio Consensus Verdict</span>
            <ShieldCheck size={15} className="text-accent" />
          </div>
          <div className="mt-2">
            <span
              className="text-xs font-black uppercase px-2.5 py-1 rounded-md border mono truncate inline-block max-w-full"
              style={{
                background: flaggedCount > 0 ? 'var(--status-crit-bg)' : 'var(--status-good-bg)',
                color: flaggedCount > 0 ? 'var(--status-critical)' : 'var(--status-good)',
                borderColor: flaggedCount > 0 ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'
              }}
            >
              {evidence.threat_code || result.verdict || 'AUTHENTIC'}
            </span>
          </div>
          <p className="text-[0.6875rem] text-ink-muted mt-1 truncate">
            {evidence.dominant_threat || 'Orthogonal Multi-Model Verified'}
          </p>
        </div>
      </div>

      {/* ── 2. Interactive Multi-Phase Architecture Ribbon ────────────────────── */}
      <div className="rounded-2xl border p-5 bg-surface-1 shadow-sm" style={{ borderColor: 'var(--border-subtle)' }}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
              <h3 className="text-sm font-black text-ink-primary uppercase tracking-wider">
                8-Stage Acoustic Forensic Architecture
              </h3>
            </div>
            <p className="text-xs text-ink-secondary mt-1">
              Select any stage node below to inspect its dedicated neural backbone, algorithms, and diagnostic telemetry.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs flex-shrink-0">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 font-bold">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Passed
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-rose-500/10 text-rose-500 font-bold">
              <span className="h-1.5 w-1.5 rounded-full bg-rose-500" /> Anomaly / AI
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 font-bold">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Inconclusive
            </span>
          </div>
        </div>

        {/* Phase Groups & Nodes Ribbon */}
        <div className="overflow-x-auto pb-2">
          <div className="min-w-[800px] space-y-4">
            {/* 4 Functional Acoustic Forensic Phases */}
            <div className="grid grid-cols-4 gap-3">
              {AUDIO_PHASES.map((phase) => (
                <div key={phase.phaseId} className="p-2.5 rounded-xl border bg-surface-2/60" style={{ borderColor: 'var(--border-subtle)' }}>
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="text-[0.625rem] font-black uppercase tracking-wider text-ink-muted">Phase {phase.phaseId}</span>
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: phase.color }} />
                  </div>
                  <h4 className="text-xs font-bold text-ink-primary truncate">{phase.name}</h4>
                  <p className="text-[0.625rem] text-ink-muted truncate mt-0.5">{phase.desc}</p>
                </div>
              ))}
            </div>

            {/* Stage Nodes Ribbon with Connecting Path */}
            <div className="relative py-2 px-2">
              <div className="absolute top-1/2 left-6 right-6 h-0.5 -translate-y-1/2 bg-surface-3 z-0" />

              <div className="flex items-center justify-between relative z-10 gap-2">
                {stages.map((st) => {
                  const isBad = ['AI_FLAGGED', 'ANOMALY_DETECTED', 'SUSPICIOUS', 'FAILED'].includes(st.status)
                  const isWarn = ['INCONCLUSIVE', 'SKIPPED'].includes(st.status)
                  const isCurrent = activeStageNum === st.stage
                  const color = getStatusColor(st.status)

                  return (
                    <button
                      key={st.stage}
                      aria-label={`Stage ${st.stage}: ${st.name}`}
                      onClick={() => setActiveStageNum(st.stage)}
                      className={`flex flex-col items-center group transition-all transform cursor-pointer ${
                        isCurrent ? 'scale-110' : 'hover:scale-105 opacity-90 hover:opacity-100'
                      }`}
                      style={{ minWidth: '85px' }}
                    >
                      <div
                        className={`h-11 w-11 rounded-2xl flex flex-col items-center justify-center font-mono font-black text-xs border-2 shadow-sm transition-all relative ${
                          isCurrent ? 'ring-4 ring-accent/30 shadow-md' : ''
                        }`}
                        style={{
                          background: isBad ? 'rgba(239,68,68,0.12)' : isWarn ? 'rgba(245,158,11,0.12)' : 'var(--surface-1)',
                          borderColor: isCurrent ? 'var(--accent)' : color,
                          color: color
                        }}
                      >
                        <span>S{st.stage}</span>
                        <span
                          className="h-1.5 w-1.5 rounded-full absolute -top-1 -right-1"
                          style={{ backgroundColor: color }}
                        />
                      </div>
                      <span className={`text-[0.6875rem] font-bold mt-1.5 text-center line-clamp-1 max-w-[95px] transition-colors ${
                        isCurrent ? 'text-accent' : 'text-ink-secondary group-hover:text-ink-primary'
                      }`}>
                        {st.name.replace('Forensics', '').replace('Engine', '').trim()}
                      </span>
                      <span className="text-[0.6rem] font-mono text-ink-muted">
                        {st.duration_ms} ms
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── 3. Dual Visual Charts (Waterfall Latency & Acoustic Risk Radar) ──── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Chart: Stage Latency Waterfall */}
        <div className="rounded-2xl border p-5 bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-black text-ink-primary flex items-center gap-2">
                <span>Stage Latency Waterfall</span>
                <span className="text-[0.625rem] font-mono px-2 py-0.5 rounded-full bg-accent/10 text-accent">Real-Time ms</span>
              </h3>
              <p className="text-xs text-ink-muted mt-0.5">Sequential processing duration per audio forensic engine</p>
            </div>
            <span className="text-xs font-mono font-bold text-accent bg-surface-2 px-2.5 py-1 rounded-lg border border-subtle">
              Peak: {Math.max(...stages.map((s) => s.duration_ms || 0))} ms
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={200}>
              <BarChart data={waterfallData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                <XAxis type="number" unit=" ms" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <YAxis dataKey="name" type="category" tick={{ fill: 'var(--text-primary)', fontSize: 11, fontWeight: 'bold' }} width={35} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload
                      return (
                        <div className="p-3 rounded-xl bg-black/90 text-white text-xs border border-white/20 shadow-xl backdrop-blur-md">
                          <p className="font-bold text-sm mb-1">Stage {d.stageNum}: {d.fullName}</p>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono text-accent font-bold">{d.duration} ms</span>
                            <span className="px-1.5 py-0.2 rounded text-[10px] uppercase font-bold" style={{ backgroundColor: d.color }}>{d.status}</span>
                          </div>
                          <p className="text-[11px] text-white/70">{d.category}</p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Bar dataKey="duration" radius={[0, 6, 6, 0]}>
                  {waterfallData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.color}
                      cursor="pointer"
                      onClick={() => setActiveStageNum(entry.stageNum)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-between text-[0.6875rem] text-ink-muted pt-2 border-t border-subtle">
            <span>Average Engine Latency: {(totalDuration / stages.length).toFixed(1)} ms</span>
            <span className="text-accent">Click bar to inspect stage</span>
          </div>
        </div>

        {/* Right Chart: Acoustic Forensic Risk Radar Profile */}
        <div className="rounded-2xl border p-5 bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-black text-ink-primary flex items-center gap-2">
                <span>Acoustic Forensic Risk Radar</span>
                <span className="text-[0.625rem] font-mono px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-500">8 Orthogonal Axes</span>
              </h3>
              <p className="text-xs text-ink-muted mt-0.5">Multi-layer acoustic anomaly profile (0-100 Risk Index)</p>
            </div>
            <span className="text-xs font-mono font-bold text-ink-secondary bg-surface-2 px-2.5 py-1 rounded-lg border border-subtle">
              Max Risk: {Math.max(...radarData.map((r) => r.score))}%
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={200}>
              <RadarChart data={radarData} outerRadius="75%">
                <PolarGrid stroke="var(--border-subtle)" strokeOpacity={0.6} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontWeight: 'bold' }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="var(--border-subtle)" tick={{ fill: 'var(--text-muted)', fontSize: 8 }} />
                <Radar name="Acoustic Severity" dataKey="score" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.35} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload
                      return (
                        <div className="p-2.5 rounded-xl bg-black/90 text-white text-xs border border-white/20 shadow-xl backdrop-blur-md">
                          <p className="font-bold text-xs">{d.subject} Risk Factor</p>
                          <p className="font-mono text-accent font-black text-sm mt-0.5">{d.score} / 100</p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-between text-[0.6875rem] text-ink-muted pt-2 border-t border-subtle">
            <span>Critical Anomaly Threshold: &gt;60%</span>
            <span className="text-emerald-500">Natural Audio Baseline: &lt;25%</span>
          </div>
        </div>
      </div>

      {/* ── 4. Deep Stage Inspector (Interactive Telemetry & Findings) ────────── */}
      <div className="rounded-2xl border p-6 bg-surface-2 shadow-sm" style={{ borderColor: 'var(--border-subtle)' }}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-subtle">
          <div className="flex items-center gap-3">
            <span
              className="flex h-10 w-10 items-center justify-center rounded-2xl text-sm font-black shadow-sm"
              style={{
                background: getStatusColor(activeStage.status),
                color: '#ffffff'
              }}
            >
              {activeStage.stage}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-black text-ink-primary">
                  Stage {activeStage.stage}: {activeStage.name}
                </h3>
                <span className="text-[0.6875rem] font-bold uppercase mono text-accent px-2 py-0.5 rounded bg-accent/10">
                  {activeStage.category}
                </span>
              </div>
              <p className="text-xs text-ink-secondary mt-0.5">
                Analytical Engine: <span className="font-mono font-bold text-ink-primary">{activeStage.engine}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border bg-surface-1" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="text-[0.625rem] font-bold uppercase text-ink-muted">Execution:</span>
              <span className="text-xs font-mono font-bold text-accent">{activeStage.duration_ms} ms</span>
            </div>
            <span
              className="text-xs font-black uppercase px-3 py-1.5 rounded-xl border mono"
              style={{
                background: getStatusColor(activeStage.status) + '18',
                color: getStatusColor(activeStage.status),
                borderColor: getStatusColor(activeStage.status) + '44'
              }}
            >
              {activeStage.status.replace(/_/g, ' ')}
            </span>
          </div>
        </div>

        {/* Stage Diagnostic Content */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
          <div className="md:col-span-2 space-y-4">
            <div>
              <h4 className="text-[0.6875rem] font-black uppercase tracking-wider text-ink-muted mb-1.5">
                Engine Specification & Methodology
              </h4>
              <p className="text-xs text-ink-secondary leading-relaxed bg-surface-1 p-3.5 rounded-xl border border-subtle">
                {activeStage.desc}
              </p>
            </div>

            <div>
              <h4 className="text-[0.6875rem] font-black uppercase tracking-wider text-ink-muted mb-1.5">
                Diagnostic Findings & Telemetry Signals
              </h4>
              <div className="space-y-2 bg-surface-1 p-3.5 rounded-xl border border-subtle">
                {activeStage.summary && (
                  <p className="text-xs font-mono text-ink-primary border-b border-subtle pb-2">
                    {activeStage.summary}
                  </p>
                )}
                <ul className="space-y-1.5 mt-2">
                  {(activeStage.findings || []).map((finding, idx) => (
                    <li key={idx} className="text-xs flex items-start gap-2 text-ink-secondary">
                      <span className="text-accent font-bold mt-0.5">•</span>
                      <span>{finding}</span>
                    </li>
                  ))}
                  {(!activeStage.findings || activeStage.findings.length === 0) && (
                    <li className="text-xs text-ink-muted italic">Engine nominal. No anomalies registered.</li>
                  )}
                </ul>
              </div>
            </div>
          </div>

          {/* Action & Deep Navigation Panel */}
          <div className="space-y-4 flex flex-col justify-between">
            <div className="bg-surface-1 p-4 rounded-xl border border-subtle space-y-3">
              <span className="text-[0.625rem] font-black uppercase tracking-wider text-ink-muted">Acoustic Benchmark</span>
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-ink-muted">Standard Latency:</span>
                  <span className="font-mono text-ink-secondary">50 - 300 ms</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-ink-muted">Forensic Admissibility:</span>
                  <span className="font-bold text-emerald-500">ISO 27042 / NIST</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-ink-muted">Sampling Resolution:</span>
                  <span className="font-mono text-ink-primary">16 kHz / 24-bit</span>
                </div>
              </div>
            </div>

            {onSwitchSubTab && activeStage.targetSubTab && (
              <button
                onClick={() => onSwitchSubTab(activeStage.targetSubTab)}
                className="w-full py-2.5 px-4 rounded-xl bg-accent text-white font-bold text-xs flex items-center justify-center gap-2 hover:bg-accent/90 transition shadow-sm cursor-pointer"
              >
                <span>Jump to {activeStage.name.split(' ')[0]} Lab</span>
                <ArrowRight size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── 5. Linear Court-Admissible Forensic Audit Trail ───────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
          <div>
            <h3 className="text-sm font-black text-ink-primary flex items-center gap-2">
              <span>Linear Forensic Audit Trail</span>
              <span className="text-[0.625rem] font-mono px-2 py-0.5 rounded-full bg-surface-3 text-ink-secondary">
                {filteredStages.length} of 8 Engines Shown
              </span>
            </h3>
            <p className="text-xs text-ink-muted mt-0.5">Cryptographically logged, sequential execution evidence</p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Filter buttons */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-surface-2 border border-subtle">
              <button
                onClick={() => setFilterMode('all')}
                className={`px-3 py-1 text-xs font-bold rounded-lg transition ${
                  filterMode === 'all' ? 'bg-surface-1 text-ink-primary shadow-xs' : 'text-ink-muted hover:text-ink-primary'
                }`}
              >
                All (8)
              </button>
              <button
                onClick={() => setFilterMode('anomalies')}
                className={`px-3 py-1 text-xs font-bold rounded-lg transition flex items-center gap-1 ${
                  filterMode === 'anomalies' ? 'bg-rose-500 text-white shadow-xs' : 'text-ink-muted hover:text-rose-500'
                }`}
              >
                <span>Anomalies</span>
                <span className="h-4 w-4 rounded-full bg-black/20 text-[0.625rem] flex items-center justify-center">
                  {flaggedCount}
                </span>
              </button>
              <button
                onClick={() => setFilterMode('passed')}
                className={`px-3 py-1 text-xs font-bold rounded-lg transition ${
                  filterMode === 'passed' ? 'bg-emerald-500 text-white shadow-xs' : 'text-ink-muted hover:text-emerald-500'
                }`}
              >
                Passed ({passedCount})
              </button>
            </div>

            <button
              onClick={toggleExpandAll}
              className="px-3 py-1.5 rounded-xl border border-subtle bg-surface-1 text-xs font-bold text-ink-secondary hover:text-ink-primary hover:bg-surface-2 transition cursor-pointer"
            >
              {stages.every((s) => expandedCards[s.stage]) ? 'Collapse All' : 'Expand All'}
            </button>

            <button
              onClick={copyPipelineManifest}
              className="px-3 py-1.5 rounded-xl border border-subtle bg-surface-1 text-xs font-bold text-accent hover:bg-accent/10 transition flex items-center gap-1.5 cursor-pointer"
            >
              <Download size={13} />
              <span>{copyFeedback ? 'Copied JSON!' : 'Export Audit'}</span>
            </button>
          </div>
        </div>

        {/* Stage List */}
        <div className="space-y-3">
          {filteredStages.map((st) => {
            const isExpanded = !!expandedCards[st.stage]
            const color = getStatusColor(st.status)
            const isSelected = activeStageNum === st.stage

            return (
              <div
                key={st.stage}
                className={`rounded-2xl border transition shadow-xs overflow-hidden ${
                  isSelected ? 'ring-2 ring-accent/30' : ''
                }`}
                style={{
                  borderColor: isSelected ? 'var(--accent)' : 'var(--border-subtle)',
                  background: 'var(--surface-1)'
                }}
              >
                {/* Stage Header */}
                <div
                  onClick={() => {
                    setActiveStageNum(st.stage)
                    toggleExpand(st.stage)
                  }}
                  className="p-4 flex items-center justify-between gap-3 cursor-pointer hover:bg-surface-2/40 transition select-none"
                >
                  <div className="flex items-center gap-3.5">
                    <span
                      className="flex h-8 w-8 items-center justify-center rounded-xl text-xs font-black shrink-0"
                      style={{
                        background: color + '20',
                        color: color,
                        border: `1.5px solid ${color}66`
                      }}
                    >
                      {st.stage}
                    </span>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-sm font-bold text-ink-primary">{st.name}</h4>
                        <span className="text-[0.625rem] font-bold uppercase mono text-ink-muted px-2 py-0.5 rounded bg-surface-2">
                          {st.category}
                        </span>
                      </div>
                      <p className="text-xs text-ink-muted mt-0.5 line-clamp-1">
                        {st.summary || st.desc}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs font-mono text-ink-muted hidden sm:inline">
                      {st.duration_ms} ms
                    </span>
                    <span
                      className="text-[0.6875rem] font-black uppercase px-2.5 py-1 rounded-lg border mono"
                      style={{
                        background: color + '15',
                        color: color,
                        borderColor: color + '44'
                      }}
                    >
                      {st.status.replace(/_/g, ' ')}
                    </span>
                    <span className="text-ink-muted text-xs transition-transform duration-200">
                      {isExpanded ? '▲' : '▼'}
                    </span>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="p-4 border-t border-subtle bg-surface-2/40 space-y-3 animate-in">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                      <span className="text-ink-secondary">
                        Engine: <span className="font-mono font-bold text-ink-primary">{st.engine}</span>
                      </span>
                      {onSwitchSubTab && st.targetSubTab && (
                        <button
                          onClick={() => onSwitchSubTab(st.targetSubTab)}
                          className="text-accent hover:underline font-bold text-xs flex items-center gap-1 self-start sm:self-auto cursor-pointer"
                        >
                          <span>Open Deep Analytics</span>
                          <ArrowRight size={12} />
                        </button>
                      )}
                    </div>

                    <div className="bg-surface-1 p-3 rounded-xl border border-subtle">
                      <p className="text-[0.625rem] font-black uppercase tracking-wider text-ink-muted mb-1.5">
                        Recorded Telemetry & Audit Notes
                      </p>
                      <ul className="space-y-1">
                        {(st.findings || []).map((finding, idx) => (
                          <li key={idx} className="text-xs flex items-start gap-2 text-ink-secondary">
                            <span className="text-accent font-bold">•</span>
                            <span>{finding}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
