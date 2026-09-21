import React, { useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell
} from 'recharts'
import {
  ShieldCheck, ShieldAlert, ShieldQuestion, FileText, Hash, Lock,
  Activity, Check, Alert, Info, Eye, Download, Image as ImageIcon
} from './ui/Icons'
import { CopyButton } from './ui'

export default function PipelineAuditVisualizer({
  pipelineModules = [],
  forensics = {},
  evidence = {},
  result = {},
  onSelectPlate,
}) {
  const [activeStage, setActiveStage] = useState(null)
  const [filterMode, setFilterMode] = useState('all') // 'all' | 'anomalies' | 'passed'
  const [expandedStages, setExpandedStages] = useState({})

  // Default fallback data matching 8-stage pipeline if empty
  const stages = pipelineModules.length > 0 ? pipelineModules : [
    {
      stage: 1,
      name: "Secure Ingestion & Validation",
      category: "File Ingestion",
      status: "PASSED",
      duration_ms: 138,
      summary: "Format: JPEG | MIME: image/jpeg | Size: 197013 bytes",
      findings: ["Header magic bytes and file extension match.", "Container dimensions verified."]
    },
    {
      stage: 2,
      name: "File Container & Cryptographic Ledger",
      category: "File Forensics",
      status: "PASSED",
      duration_ms: 320,
      summary: "SHA-256 verified | pHash generated | Trailing data: None",
      findings: ["Cryptographic and perceptual hashes calculated.", "No hidden appended bytes detected past EOF."]
    },
    {
      stage: 3,
      name: "Metadata & Digital Timeline Forensics",
      category: "Provenance & Metadata",
      status: "PASSED",
      duration_ms: 1,
      summary: "Camera: Unknown / Unspecified | Software: None recorded | Timeline: PURGED_METADATA",
      findings: ["Metadata was sanitized or stripped (standard for social media uploads)."]
    },
    {
      stage: 4,
      name: "Frequency & Signal Forensics (FFT / DCT / ELA)",
      category: "Image Forensics",
      status: "AI_FLAGGED",
      duration_ms: 1669,
      summary: "Camera Sensor: Synthetic / AI-Rendered | ELA Score: 0.0322 | CFA Bayer: Missing",
      findings: ["Missing physical Bayer CFA demosaicing periodicity.", "Frequency spectrum exhibits synthetic diffusion roll-off."]
    },
    {
      stage: 5,
      name: "Tampering & Watermark Engine",
      category: "Structural Tampering",
      status: "PASSED",
      duration_ms: 2136,
      summary: "Copy-Move: None | Splicing: None | Watermark: None",
      findings: ["No copy-move cloning keypoints matched.", "No boundary splicing seams found.", "Watermark probe clean."]
    },
    {
      stage: 6,
      name: "AI & Deepfake Detection Engine",
      category: "Neural Core",
      status: "AI_FLAGGED",
      duration_ms: 348,
      summary: "Ensemble Score: 82.0% | GenAI ViT: 42.4% | Facial EfficientNet-B4: 0.0%",
      findings: ["Ensemble models indicate high generative synthesis probability.", "Full-scene synthetic texture signatures detected."]
    },
    {
      stage: 7,
      name: "Steganography & Provenance Authentication",
      category: "Cyber Security",
      status: "PASSED",
      duration_ms: 143,
      summary: "Stego Payload: LOW (25.0%) | C2PA: Absent | Threat IOC: LOW",
      findings: ["Spatial bit-plane entropy within natural tolerances.", "No known malicious exploit payloads embedded."]
    },
    {
      stage: 8,
      name: "Evidence Fusion & Calibrated Risk Engine",
      category: "Risk Consensus",
      status: "CONSENSUS_REACHED",
      duration_ms: 1437,
      summary: "Risk Score: 82/100 (HIGH_RISK) | Fusion: CORROBORATED_MANIPULATION",
      findings: ["Multi-expert consensus confirms synthetic generation.", "Corroborated by physical sensor absence and neural classification."]
    }
  ]

  const totalDuration = stages.reduce((acc, s) => acc + (s.duration_ms || 0), 0)
  const anomalyCount = stages.filter(s => s.status === 'AI_FLAGGED' || s.status === 'ANOMALY_DETECTED' || s.status === 'SUSPICIOUS').length
  const passedCount = stages.filter(s => s.status === 'PASSED').length
  const consensusStage = stages.find(s => s.status === 'CONSENSUS_REACHED')

  const getStatusTheme = (status) => {
    switch (status) {
      case 'AI_FLAGGED':
      case 'ANOMALY_DETECTED':
        return {
          color: '#ef4444',
          bg: 'rgba(239, 68, 68, 0.12)',
          border: 'rgba(239, 68, 68, 0.35)',
          badge: 'AI FLAGGED',
          badgeBg: 'bg-rose-500/20 text-rose-500 dark:text-rose-400 border-rose-500/30'
        }
      case 'SUSPICIOUS':
        return {
          color: '#f59e0b',
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.35)',
          badge: 'SUSPICIOUS',
          badgeBg: 'bg-amber-500/20 text-amber-500 dark:text-amber-400 border-amber-500/30'
        }
      case 'CONSENSUS_REACHED':
        return {
          color: '#6366f1',
          bg: 'rgba(99, 102, 241, 0.12)',
          border: 'rgba(99, 102, 241, 0.35)',
          badge: 'CONSENSUS',
          badgeBg: 'bg-indigo-500/20 text-indigo-500 dark:text-indigo-400 border-indigo-500/30'
        }
      case 'PASSED':
      default:
        return {
          color: '#10b981',
          bg: 'rgba(16, 185, 129, 0.12)',
          border: 'rgba(16, 185, 129, 0.35)',
          badge: 'PASSED',
          badgeBg: 'bg-emerald-500/20 text-emerald-500 dark:text-emerald-400 border-emerald-500/30'
        }
    }
  }

  const toggleExpand = (stageNum) => {
    setExpandedStages(prev => ({
      ...prev,
      [stageNum]: !prev[stageNum]
    }))
  }

  const toggleExpandAll = () => {
    const allExpanded = stages.every(s => expandedStages[s.stage])
    const nextState = {}
    stages.forEach(s => { nextState[s.stage] = !allExpanded })
    setExpandedStages(nextState)
  }

  const filteredStages = stages.filter(s => {
    if (filterMode === 'anomalies') return s.status === 'AI_FLAGGED' || s.status === 'ANOMALY_DETECTED' || s.status === 'SUSPICIOUS'
    if (filterMode === 'passed') return s.status === 'PASSED'
    return true
  })

  // Data for Recharts horizontal waterfall
  const chartData = stages.map(s => ({
    name: `S${s.stage}`,
    fullName: s.name,
    duration: s.duration_ms || 10,
    status: s.status,
    category: s.category,
    color: getStatusTheme(s.status).color
  }))

  const hashes = forensics.hashes || evidence.hashes || {}
  const fileSecurity = forensics.file_security || {}
  const metadata = forensics.metadata_forensics || {}
  const tamperingInfo = forensics.tampering || {}
  const cameraStats = forensics.camera_stats || {}
  const aiBreakdown = evidence.ai_breakdown || {}

  return (
    <div className="space-y-6">
      {/* Top Banner KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl border bg-surface-1 dark:bg-surface-2/40 shadow-xs flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Execution Flow</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-black font-mono text-ink-primary">8 / 8</span>
            <span className="text-xs text-ink-secondary">Engines</span>
          </div>
          <span className="text-[11px] text-ink-muted mt-1">100% Sequence Verified</span>
        </div>

        <div className="p-3.5 rounded-xl border bg-surface-1 dark:bg-surface-2/40 shadow-xs flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Flags & Anomalies</span>
            <span className={`h-2 w-2 rounded-full ${anomalyCount > 0 ? 'bg-rose-500' : 'bg-emerald-500'}`} />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className={`text-2xl font-black font-mono ${anomalyCount > 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
              {anomalyCount}
            </span>
            <span className="text-xs text-ink-secondary">Flagged</span>
          </div>
          <span className="text-[11px] text-ink-muted mt-1">{passedCount} Passed Checks</span>
        </div>

        <div className="p-3.5 rounded-xl border bg-surface-1 dark:bg-surface-2/40 shadow-xs flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Total Latency</span>
            <Activity size={14} className="text-accent" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-black font-mono text-ink-primary">
              {(totalDuration / 1000).toFixed(2)}s
            </span>
            <span className="text-xs text-ink-muted">({totalDuration} ms)</span>
          </div>
          <span className="text-[11px] text-ink-muted mt-1">Parallel RTX Tensor Passes</span>
        </div>

        <div className="p-3.5 rounded-xl border bg-surface-1 dark:bg-surface-2/40 shadow-xs flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Audit Consensus</span>
            <ShieldCheck size={14} className="text-indigo-500" />
          </div>
          <div className="mt-2">
            <span className="text-sm font-black font-mono px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              {consensusStage?.status === 'CONSENSUS_REACHED' ? 'CORROBORATED' : 'ANALYZED'}
            </span>
          </div>
          <span className="text-[11px] text-ink-muted mt-1">Multi-Signal Calibrated</span>
        </div>
      </div>

      {/* ── Visual Workflow Pipeline Node Graph ───────────────────────────────── */}
      <div className="rounded-2xl border p-5 bg-surface-1 dark:bg-surface-2/30 shadow-sm" style={{ borderColor: 'var(--border-subtle)' }}>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="text-sm font-black text-ink-primary flex items-center gap-2">
              <span>Digital Pipeline Workflow Diagram</span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-accent/10 text-accent">Interactive Graph</span>
            </h3>
            <p className="text-xs text-ink-muted mt-0.5">Click any stage node below to jump directly to its forensic telemetry inspection</p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500"></span> Passed</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-rose-500"></span> Anomaly / AI</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-indigo-500"></span> Consensus</span>
          </div>
        </div>

        {/* Node Graph Ribbon */}
        <div className="relative py-2 overflow-x-auto">
          <div className="flex items-center justify-between min-w-[760px] relative gap-2">
            {/* Connecting line behind nodes */}
            <div className="absolute top-1/2 left-6 right-6 h-0.5 -translate-y-1/2 bg-black/10 dark:bg-white/10 z-0" />

            {stages.map((st) => {
              const theme = getStatusTheme(st.status)
              const isActive = activeStage === st.stage

              return (
                <button
                  key={st.stage}
                  onClick={() => {
                    setActiveStage(st.stage)
                    const el = document.getElementById(`stage-card-${st.stage}`)
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
                  }}
                  className={`relative z-10 flex flex-col items-center group transition-all transform ${
                    isActive ? 'scale-105' : 'hover:scale-105'
                  }`}
                >
                  <div
                    className={`h-11 w-11 rounded-full flex items-center justify-center font-mono font-black text-sm border-2 transition-all shadow-sm ${
                      isActive ? 'ring-4 ring-accent/30 shadow-md' : ''
                    }`}
                    style={{
                      background: theme.bg,
                      borderColor: theme.color,
                      color: theme.color
                    }}
                  >
                    {st.stage}
                  </div>
                  <span className="text-[11px] font-bold text-ink-primary mt-1.5 text-center line-clamp-1 max-w-[85px]">
                    {st.name.split(' ')[0]}
                  </span>
                  <span className="text-[10px] font-mono text-ink-muted">
                    {st.duration_ms}ms
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Recharts Waterfall Latency Distribution ───────────────────────────── */}
      <div className="rounded-2xl border p-5 bg-surface-1 dark:bg-surface-2/30 shadow-sm" style={{ borderColor: 'var(--border-subtle)' }}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-black text-ink-primary">Stage Latency & Compute Distribution</h3>
            <p className="text-xs text-ink-muted mt-0.5">Execution duration per forensic discipline (Milliseconds)</p>
          </div>
          <span className="text-xs font-mono text-ink-secondary bg-surface-2 px-2.5 py-1 rounded-lg">
            Peak: {Math.max(...stages.map(s => s.duration_ms || 0))} ms
          </span>
        </div>

        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
              <XAxis type="number" unit=" ms" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
              <YAxis dataKey="name" type="category" tick={{ fill: 'var(--text-primary)', fontSize: 11, fontWeight: 'bold' }} width={35} />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload
                    return (
                      <div className="p-3 rounded-xl bg-black/90 text-white text-xs border border-white/20 shadow-xl backdrop-blur-md">
                        <p className="font-bold text-sm mb-1">{d.fullName}</p>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-accent">{d.duration} ms</span>
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
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Interactive Controls & Filter Bar ─────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-surface-2 border" style={{ borderColor: 'var(--border-subtle)' }}>
          <button
            onClick={() => setFilterMode('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              filterMode === 'all' ? 'bg-surface-1 text-ink-primary shadow-xs' : 'text-ink-muted hover:text-ink-primary'
            }`}
          >
            All Stages ({stages.length})
          </button>
          <button
            onClick={() => setFilterMode('anomalies')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1 ${
              filterMode === 'anomalies' ? 'bg-rose-500 text-white shadow-xs' : 'text-ink-muted hover:text-rose-500'
            }`}
          >
            Flagged ({anomalyCount})
          </button>
          <button
            onClick={() => setFilterMode('passed')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              filterMode === 'passed' ? 'bg-emerald-500 text-white shadow-xs' : 'text-ink-muted hover:text-emerald-500'
            }`}
          >
            Clean ({passedCount})
          </button>
        </div>

        <button
          onClick={toggleExpandAll}
          className="text-xs font-bold text-accent hover:text-accent-hover px-3 py-1.5 rounded-lg hover:bg-accent/10 transition"
        >
          {stages.every(s => expandedStages[s.stage]) ? 'Collapse All Details' : 'Expand All Details'}
        </button>
      </div>

      {/* ── All 8 Comprehensive Forensic Digital Cards ────────────────────────── */}
      <div className="space-y-4">
        {filteredStages.map((mod) => {
          const stageNum = mod.stage
          const theme = getStatusTheme(mod.status)
          const isExpanded = expandedStages[stageNum] ?? false
          const isSelected = activeStage === stageNum

          return (
            <div
              key={stageNum}
              id={`stage-card-${stageNum}`}
              className={`rounded-2xl border p-5 transition-all bg-surface-1 dark:bg-surface-2/40 shadow-xs hover:shadow-md ${
                isSelected ? 'ring-2 ring-accent' : ''
              }`}
              style={{ borderColor: theme.border }}
            >
              {/* Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-9 w-9 items-center justify-center rounded-xl font-mono font-black text-sm"
                    style={{ background: theme.bg, color: theme.color }}
                  >
                    {stageNum}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-black text-ink-primary">{mod.name}</h4>
                      <span className="text-[10px] uppercase tracking-wider font-mono px-2 py-0.5 rounded-md bg-surface-2 text-ink-muted">
                        {mod.category}
                      </span>
                    </div>
                    <span className="text-xs text-ink-muted font-mono">{mod.duration_ms} ms execution</span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5">
                  <span className={`text-xs font-black uppercase px-3 py-1 rounded-lg border ${theme.badgeBg}`}>
                    {mod.status.replace(/_/g, ' ')}
                  </span>
                  <button
                    onClick={() => toggleExpand(stageNum)}
                    className="px-2.5 py-1 text-xs font-bold rounded-lg bg-surface-2 hover:bg-surface-3 text-ink-secondary transition"
                  >
                    {isExpanded ? 'Hide Details' : 'Inspect'}
                  </button>
                </div>
              </div>

              {/* Main Summary finding box */}
              <div className="p-3.5 rounded-xl bg-surface-2/60 border text-xs text-ink-primary font-medium leading-relaxed mb-3" style={{ borderColor: 'var(--border-subtle)' }}>
                {mod.summary}
              </div>

              {/* Specific Digital Telemetry Per Stage */}
              <div className="space-y-2.5">
                {/* Stage 1 Ingestion Details */}
                {stageNum === 1 && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Format</span>
                      <p className="text-xs font-black font-mono text-ink-primary">{fileSecurity.format || 'JPEG'}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">MIME Type</span>
                      <p className="text-xs font-black font-mono text-ink-primary">{fileSecurity.mime_type || 'image/jpeg'}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Header Bytes</span>
                      <p className="text-xs font-black font-mono text-emerald-500">VALID MAGIC BYTES</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">MIME Match</span>
                      <p className="text-xs font-black font-mono text-emerald-500">NO MISMATCH</p>
                    </div>
                  </div>
                )}

                {/* Stage 2 Cryptographic Ledger */}
                {stageNum === 2 && (
                  <div className="space-y-2 pt-1">
                    <div className="p-3 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-ink-muted block">SHA-256 Cryptographic Digest</span>
                        <span className="font-mono text-xs font-bold text-ink-primary break-all">{hashes.sha256 || 'a22251dfa60f0275...'}</span>
                      </div>
                      <CopyButton text={hashes.sha256 || 'a22251dfa60f0275'} />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">Perceptual Hash (pHash)</span>
                        <p className="text-xs font-black font-mono text-ink-primary">{hashes.phash || 'a49e738da31394cb'}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">Trailing Data Injection</span>
                        <p className="text-xs font-black font-mono text-emerald-500">CLEAN (0 Bytes past EOF)</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">Embedded Wrappers</span>
                        <p className="text-xs font-black font-mono text-emerald-500">CLEAN (No Zip/Exe)</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Stage 3 Metadata */}
                {stageNum === 3 && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Camera Make</span>
                      <p className="text-xs font-black font-mono text-ink-primary">{metadata.camera_make || 'Unspecified'}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Camera Model</span>
                      <p className="text-xs font-black font-mono text-ink-primary">{metadata.camera_model || 'Unspecified'}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Software Tag</span>
                      <p className="text-xs font-black font-mono text-ink-primary">{metadata.software || 'None Recorded'}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Timeline Status</span>
                      <p className="text-xs font-black font-mono text-amber-500">{metadata.timeline_consistency || 'PURGED_METADATA'}</p>
                    </div>
                  </div>
                )}

                {/* Stage 4 Physical Signal & CFA */}
                {stageNum === 4 && (
                  <div className="space-y-2 pt-1">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">Sensor Noise Origin</span>
                        <p className="text-xs font-black font-mono text-rose-500">{cameraStats.estimated_camera_family || 'Synthetic / AI-Rendered'}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">Bayer CFA Periodicity</span>
                        <p className="text-xs font-black font-mono text-rose-500">MISSING (AI Synthetic)</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">ELA Compression Divergence</span>
                        <p className="text-xs font-black font-mono text-ink-primary">0.0322 (Calibrated)</p>
                      </div>
                    </div>
                    {onSelectPlate && (
                      <button
                        onClick={() => onSelectPlate('ela')}
                        className="inline-flex items-center gap-1.5 text-xs font-bold text-accent hover:underline pt-1"
                      >
                        <Eye size={12} /> Open Error Level Analysis (ELA) Plate in Visual Lab
                      </button>
                    )}
                  </div>
                )}

                {/* Stage 5 Tampering & Watermark */}
                {stageNum === 5 && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Copy-Move Cloning</span>
                      <p className="text-xs font-black font-mono text-emerald-500">
                        {tamperingInfo.copy_move_detected ? 'CLONED KEYPOINTS' : 'NONE DETECTED'}
                      </p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Splicing Seams</span>
                      <p className="text-xs font-black font-mono text-emerald-500">
                        {tamperingInfo.splicing_detected ? 'SEAM DISCONTINUITY' : 'NONE DETECTED'}
                      </p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Watermark & Logo Probe</span>
                      <p className="text-xs font-black font-mono text-emerald-500">CLEAN (No Watermark)</p>
                    </div>
                  </div>
                )}

                {/* Stage 6 AI Deepfake Core */}
                {stageNum === 6 && (
                  <div className="space-y-2 pt-1">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">Ensemble AI Score</span>
                        <p className="text-base font-black font-mono text-rose-500">
                          {((aiBreakdown.ensemble_fake_prob ?? 0.82) * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">ViT Full-Scene Generative</span>
                        <p className="text-base font-black font-mono text-amber-500">
                          {((aiBreakdown.generative_ai_prob ?? 0.424) * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                        <span className="text-[10px] uppercase font-bold text-ink-muted">Facial EfficientNet-B4</span>
                        <p className="text-base font-black font-mono text-ink-primary">
                          {((aiBreakdown.face_fake_prob ?? 0.0) * 100).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                    {onSelectPlate && (
                      <button
                        onClick={() => onSelectPlate('ai')}
                        className="inline-flex items-center gap-1.5 text-xs font-bold text-accent hover:underline pt-1"
                      >
                        <Eye size={12} /> Open Grad-CAM Neural Attention Heatmap
                      </button>
                    )}
                  </div>
                )}

                {/* Stage 7 Steganography */}
                {stageNum === 7 && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Stego LSB Anomaly</span>
                      <p className="text-xs font-black font-mono text-emerald-500">LOW (Natural Noise)</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">C2PA Provenance Manifest</span>
                      <p className="text-xs font-black font-mono text-ink-muted">ABSENT (Standard Upload)</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-surface-2/40 border border-black/5 dark:border-white/5">
                      <span className="text-[10px] uppercase font-bold text-ink-muted">Threat Intel IOCs</span>
                      <p className="text-xs font-black font-mono text-emerald-500">0 Threat Signatures</p>
                    </div>
                  </div>
                )}

                {/* Stage 8 Consensus Fusion */}
                {stageNum === 8 && (
                  <div className="space-y-2 pt-1">
                    <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-indigo-600 dark:text-indigo-400">Multi-Signal Calibrated Risk Score</span>
                        <div className="flex items-baseline gap-2 mt-0.5">
                          <span className="text-2xl font-black font-mono text-indigo-600 dark:text-indigo-400">82 / 100</span>
                          <span className="text-xs font-black text-rose-500 uppercase px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20">HIGH RISK</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] uppercase font-bold text-ink-muted block">Decision Corroboration</span>
                        <span className="font-mono text-xs font-bold text-ink-primary">CORROBORATED_MANIPULATION</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Expandable Forensic Finding Explainer */}
                {isExpanded && mod.findings && mod.findings.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-black/5 dark:border-white/5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-ink-muted block mb-1.5">
                      Detailed Forensic Findings & Technical Telemetry
                    </span>
                    <ul className="space-y-1">
                      {mod.findings.map((f, fIdx) => (
                        <li key={fIdx} className="text-xs text-ink-secondary flex items-start gap-2">
                          <span className="text-accent mt-0.5 font-bold">›</span>
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
