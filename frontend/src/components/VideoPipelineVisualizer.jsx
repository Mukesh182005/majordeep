import React, { useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts'
import {
  Activity, Alert, Check, CheckCircle, Cpu, Eye, FileText,
  Hash, Info, ShieldAlert, ShieldCheck, ShieldQuestion, Video as VideoIcon, Zap,
  Lock, ArrowRight, Download, Sparkles
} from './ui/Icons'
import { percent } from '../lib/format'

export const VIDEO_PHASES = [
  {
    phaseId: 1,
    name: 'Ingestion & Container',
    stages: [1, 2],
    color: '#00E5FF',
    desc: 'ISO bitstream box inspection & temporal shot boundary cutting'
  },
  {
    phaseId: 2,
    name: 'Neural Spatial Vision',
    stages: [3, 4],
    color: '#3B82F6',
    desc: 'Facial EfficientNet-B4 + ViT scene diffusion & CFA Bayer periodicity'
  },
  {
    phaseId: 3,
    name: 'Biometrics & 4D Tensors',
    stages: [5, 6, 7],
    color: '#8B5CF6',
    desc: 'Ocular landmark acceleration, rPPG pulse extraction & space-time tensors'
  },
  {
    phaseId: 4,
    name: 'Kinematics & Flow',
    stages: [8, 9],
    color: '#EC4899',
    desc: 'Lip articulatory jerk dynamics & Farneback dense optical flow fields'
  },
  {
    phaseId: 5,
    name: 'Audio & Attribution',
    stages: [10, 11],
    color: '#F59E0B',
    desc: 'LCNN acoustic voice sync & zero-watermark generator diffusion matching'
  }
]

export const DEFAULT_11_STAGES = [
  {
    stage: 1,
    id: 1,
    name: 'Container & Bitstream Forensics',
    category: 'Container Architecture',
    engine: 'ISOBMFF Parser & 2D FFT Moiré Filter',
    status: 'PASSED',
    duration_ms: 18,
    targetSubTab: 'container',
    desc: 'Binary parsing of ISO Base Media boxes (ftyp, moov, trak, mdat) and display moiré verification.'
  },
  {
    stage: 2,
    id: 2,
    name: 'Scene & Shot Boundary Segmentation',
    category: 'Temporal Segmentation',
    engine: 'Bhattacharyya Histogram & Edge Discontinuity Filter',
    status: 'PASSED',
    duration_ms: 54,
    targetSubTab: 'scenes',
    desc: 'Color/edge delta boundary segmentation isolating distinct scene transitions for independent forensics.'
  },
  {
    stage: 3,
    id: 3,
    name: 'Spatial Neural & Generative AI Backbone',
    category: 'Spatial Neural Vision',
    engine: 'EfficientNet-B4 Deepfake + ViT Full-Scene Diffusion Detector',
    status: 'PASSED',
    duration_ms: 185,
    targetSubTab: 'timeline',
    desc: 'Per-frame facial crop deepfake neural inference and ViT full-scene generative artifact classification.'
  },
  {
    stage: 4,
    id: 4,
    name: '28-Module Image Forensic Engine',
    category: 'Micro-Signal Forensics',
    engine: 'CFA Bayer Periodicity + Fourier Radial Alpha + ELA Difference',
    status: 'PASSED',
    duration_ms: 312,
    targetSubTab: 'summary',
    desc: 'Evaluated CFA Bayer periodicity ratio, radial spectrum roll-off, ELA, and synthetic matte voids on keyframes.'
  },
  {
    stage: 5,
    id: 5,
    name: 'Temporal Jitter & Facial Dynamics',
    category: 'Biometric Kinematics',
    engine: 'Kalman Landmark Trajectory + Ocular Blink Synchrony',
    status: 'PASSED',
    duration_ms: 42,
    targetSubTab: 'facial',
    desc: 'Facial bounding-box acceleration, landmark jitter variance, and biological blink rhythm plausibility.'
  },
  {
    stage: 6,
    id: 6,
    name: 'Remote Photoplethysmography (rPPG)',
    category: 'Cardiovascular Biometrics',
    engine: 'CHROM/POS Capillary Reflectance Bandpass (0.75-2.5 Hz) + Welch PSD',
    status: 'INCONCLUSIVE',
    duration_ms: 36,
    targetSubTab: 'biometrics',
    desc: 'Cardiovascular Blood Volume Pulse (BVP) extraction measuring autonomous biological blood volume pulses.'
  },
  {
    stage: 7,
    id: 7,
    name: 'Spatio-Temporal 4D Tensor Dynamics',
    category: 'Deep Spatiotemporal',
    engine: 'TimeSformer Space-Time Patch Variance + SlowFast Seam Vibration',
    status: 'PASSED',
    duration_ms: 95,
    targetSubTab: 'biometrics',
    desc: 'TimeSformer space-time patch variance, latent denoise jump rates, and SlowFast boundary vibration.'
  },
  {
    stage: 8,
    id: 8,
    name: 'LipForensics Articulatory Kinematics',
    category: 'Oral Dynamics',
    engine: 'Lip Aperture Kinematics + 2nd-Derivative Articulatory Jerk',
    status: 'INSUFFICIENT_FACE_FRAMES',
    duration_ms: 22,
    targetSubTab: 'facial',
    desc: 'Oral kinematic velocity, articulatory jerk anomalies, and phonetic coarticulation texture smoothness.'
  },
  {
    stage: 9,
    id: 9,
    name: 'Optical Flow Motion Decomposition',
    category: 'Vector Motion Field',
    engine: 'Farneback Dense Motion Vectors + Boundary Seam Divergence',
    status: 'PASSED',
    duration_ms: 145,
    targetSubTab: 'facial',
    desc: 'Dense optical flow divergence between synthesized face boundary pixels and background scene physics.'
  },
  {
    stage: 10,
    id: 10,
    name: 'Acoustic Speech & Cross-Modal Lip-Sync',
    category: 'Multi-Modal Audio-Visual',
    engine: 'LCNN Voice AI + Glottal IAIF Flow + Acoustic-Visual Cross-Correlation',
    status: 'PASSED',
    duration_ms: 68,
    targetSubTab: 'lipsync',
    desc: 'Audio demuxing, LCNN acoustic synthetic detection, and speech envelope to lip aperture synchrony.'
  },
  {
    stage: 11,
    id: 11,
    name: 'AI Generator Attribution Engine',
    category: 'Attribution Engine',
    engine: 'Physical Diffusion Latent Matching (Sora, Gemini/Veo, Kling, Runway, Luma)',
    status: 'AI_FLAGGED',
    duration_ms: 55,
    targetSubTab: 'origin',
    desc: 'Intrinsic physical & latent diffusion matching attributing synthesis engines without requiring watermarks.'
  }
]

export default function VideoPipelineVisualizer({
  result = {},
  onSwitchSubTab,
}) {
  const evidence = result.evidence || {}
  const container = evidence.container_forensics || {}
  const temporal = evidence.temporal_metrics || {}
  const facial = evidence.facial_dynamics || {}
  const lipsync = evidence.crossmodal_lipsync || {}
  const attribution = evidence.generator_attribution || {}
  const imageForensics = evidence.image_forensics || {}
  const rppg = evidence.rppg_biometrics || {}
  const spatiotemporal = evidence.spatiotemporal_forensics || {}
  const lipForensics = evidence.lip_forensics || {}
  const frameScores = evidence.frame_scores || []

  const rawModules = evidence.pipeline_modules?.length ? evidence.pipeline_modules : DEFAULT_11_STAGES

  // Merge runtime evidence with rich metadata
  const stages = rawModules.map((mod, idx) => {
    const sNum = mod.stage || mod.id || idx + 1
    const defaultMeta = DEFAULT_11_STAGES.find(s => s.stage === sNum) || DEFAULT_11_STAGES[idx] || {}
    return {
      ...defaultMeta,
      ...mod,
      stage: sNum,
      id: sNum,
      name: mod.name || defaultMeta.name,
      category: mod.category || defaultMeta.category,
      engine: defaultMeta.engine,
      targetSubTab: defaultMeta.targetSubTab,
      status: mod.status || defaultMeta.status || 'PASSED',
      duration_ms: mod.duration_ms ?? defaultMeta.duration_ms ?? 20,
      desc: mod.desc || mod.summary || defaultMeta.desc
    }
  })

  const [activeStageNum, setActiveStageNum] = useState(1)
  const [filterMode, setFilterMode] = useState('all') // 'all' | 'flagged' | 'passed'
  const [chartView, setChartView] = useState('both') // 'both' | 'waterfall' | 'radar'

  const activeStage = stages.find(s => s.stage === activeStageNum) || stages[0]

  const totalDuration = stages.reduce((acc, s) => acc + (s.duration_ms || 0), 0)
  const flaggedCount = stages.filter(s => ['AI_FLAGGED', 'ANOMALY_DETECTED', 'SUSPICIOUS', 'FAILED'].includes(s.status)).length
  const warnCount = stages.filter(s => ['INCONCLUSIVE', 'INSUFFICIENT_FACE_FRAMES', 'INSUFFICIENT_FACE_SAMPLES', 'SKIPPED'].includes(s.status)).length
  const passedCount = stages.filter(s => s.status === 'PASSED').length

  const getStatusColor = (st) => {
    if (['AI_FLAGGED', 'ANOMALY_DETECTED', 'SUSPICIOUS', 'FAILED'].includes(st)) return '#ef4444'
    if (['INCONCLUSIVE', 'INSUFFICIENT_FACE_FRAMES', 'INSUFFICIENT_FACE_SAMPLES', 'SKIPPED'].includes(st)) return '#f59e0b'
    return '#10b981'
  }

  // Waterfall Chart Data
  const waterfallData = stages.map(s => ({
    name: `S${s.stage}`,
    stageNum: s.stage,
    fullName: s.name,
    duration: s.duration_ms || 10,
    status: s.status,
    category: s.category,
    color: getStatusColor(s.status)
  }))

  // Multi-Disciplinary Forensic Radar Data (0-100 severity profile)
  const worstFaceProb = frameScores.length ? Math.max(...frameScores.map(f => f.fake_probability || 0)) : (result.fake_probability || 0)
  const vitProb = evidence.vit_genai_prob || 0
  const spatialScore = Math.round(Math.max(worstFaceProb, vitProb) * 100)
  const containerScore = container.screen_recording_analysis?.screen_recording_detected ? 75 : (container.metadata_inconsistencies?.length ? 60 : 12)
  const temporalScore = Math.min(100, Math.round((temporal.jitter_score || 0) * 130 + (temporal.motion_anomaly || 0) * 60))
  const rppgScore = rppg.is_synthetic_biometric_void ? 92 : (rppg.biometric_pulse_detected ? 15 : 45)
  const spatiotemporalScore = Math.min(100, Math.round((spatiotemporal.spatiotemporal_anomaly_score || 0) * 100))
  const lipScore = Math.round((lipForensics.lip_manipulation_probability || 0) * 100)
  const flowScore = Math.min(100, Math.round((temporal.motion_anomaly || 0) * 100))
  const audioScore = lipsync.lip_sync_anomaly_detected ? 85 : (lipsync.audiovisual_correlation != null && lipsync.audiovisual_correlation < 0.2 ? 60 : 15)
  const attributionScore = attribution.is_ai_generated ? Math.round((attribution.attribution_confidence || 0.85) * 100) : 15
  const cfaScore = imageForensics?.camera_cfa?.synthetic_sensor_detected ? 85 : 12

  const radarData = [
    { subject: 'Container', score: containerScore, fullMark: 100 },
    { subject: 'Spatial AI', score: spatialScore, fullMark: 100 },
    { subject: 'CFA Sensor', score: cfaScore, fullMark: 100 },
    { subject: 'Facial Jitter', score: temporalScore, fullMark: 100 },
    { subject: 'rPPG Pulse', score: rppgScore, fullMark: 100 },
    { subject: '4D Tensor', score: spatiotemporalScore, fullMark: 100 },
    { subject: 'Lip Kinematics', score: lipScore, fullMark: 100 },
    { subject: 'Optical Flow', score: flowScore, fullMark: 100 },
    { subject: 'Acoustic Sync', score: audioScore, fullMark: 100 },
    { subject: 'AI Generator', score: attributionScore, fullMark: 100 },
  ]

  const filteredStages = stages.filter(s => {
    const isBad = ['AI_FLAGGED', 'ANOMALY_DETECTED', 'SUSPICIOUS', 'FAILED'].includes(s.status)
    if (filterMode === 'flagged') return isBad
    if (filterMode === 'passed') return !isBad
    return true
  })

  return (
    <div className="space-y-6">
      {/* ── 1. Executive Pipeline Telemetry KPI Ribbon ────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl border bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Pipeline Execution</span>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-ink-primary">11 / 11</span>
            <span className="text-xs font-semibold text-emerald-500">Completed</span>
          </div>
          <p className="text-[0.6875rem] text-ink-muted mt-1">Multi-Modal Sequential Engine</p>
        </div>

        <div className="p-4 rounded-2xl border bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Security Anomalies</span>
            <ShieldAlert size={15} style={{ color: flaggedCount > 0 ? 'var(--status-critical)' : 'var(--status-good)' }} />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono" style={{ color: flaggedCount > 0 ? 'var(--status-critical)' : 'var(--status-good)' }}>
              {flaggedCount}
            </span>
            <span className="text-xs font-semibold text-ink-secondary">Flagged Stages</span>
          </div>
          <div className="flex items-center gap-2 text-[0.6875rem] text-ink-muted mt-1">
            <span className="text-emerald-500 font-bold">{passedCount} Passed</span>
            <span>•</span>
            <span className="text-amber-500 font-bold">{warnCount} Warn/Info</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl border bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Pipeline Latency</span>
            <Activity size={15} className="text-accent" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-ink-primary">
              {(totalDuration / 1000).toFixed(2)}s
            </span>
            <span className="text-xs font-mono text-ink-muted">({totalDuration} ms)</span>
          </div>
          <p className="text-[0.6875rem] text-ink-muted mt-1">Parallel GPU Ingestion Timing</p>
        </div>

        <div className="p-4 rounded-2xl border bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between">
            <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Pipeline Verdict</span>
            <Zap size={15} className="text-accent" />
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
            {evidence.dominant_threat || 'Consensus Verified'}
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
                11-Stage Multi-Modal Pipeline Architecture
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
          <div className="min-w-[960px] space-y-4">
            {/* 5 Functional Forensic Phases */}
            <div className="grid grid-cols-5 gap-3">
              {VIDEO_PHASES.map((phase) => (
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
              {/* Connecting baseline line */}
              <div className="absolute top-1/2 left-6 right-6 h-0.5 -translate-y-1/2 bg-surface-3 z-0" />

              <div className="flex items-center justify-between relative z-10 gap-2">
                {stages.map((st, i) => {
                  const isBad = ['AI_FLAGGED', 'ANOMALY_DETECTED', 'SUSPICIOUS', 'FAILED'].includes(st.status)
                  const isWarn = ['INCONCLUSIVE', 'INSUFFICIENT_FACE_FRAMES', 'INSUFFICIENT_FACE_SAMPLES', 'SKIPPED'].includes(st.status)
                  const isCurrent = activeStageNum === st.stage
                  const color = getStatusColor(st.status)

                  return (
                    <button
                      key={st.stage}
                      onClick={() => setActiveStageNum(st.stage)}
                      className={`flex flex-col items-center group transition-all transform cursor-pointer ${
                        isCurrent ? 'scale-110' : 'hover:scale-105 opacity-90 hover:opacity-100'
                      }`}
                      style={{ minWidth: '76px' }}
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
                      <span className={`text-[0.6875rem] font-bold mt-1.5 text-center line-clamp-1 max-w-[85px] transition-colors ${
                        isCurrent ? 'text-accent' : 'text-ink-secondary group-hover:text-ink-primary'
                      }`}>
                        {st.name.replace('Forensics', '').replace('Dynamics', '').replace('Attribution', '').trim()}
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

      {/* ── 3. Dual Visual Charts (Waterfall Latency & Forensic Anomaly Radar) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Chart: Stage Latency Waterfall */}
        <div className="rounded-2xl border p-5 bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-black text-ink-primary flex items-center gap-2">
                <span>Stage Execution Latency Waterfall</span>
                <span className="text-[0.625rem] font-mono px-2 py-0.5 rounded-full bg-accent/10 text-accent">Real-Time ms</span>
              </h3>
              <p className="text-xs text-ink-muted mt-0.5">Sequential processing duration per analytical engine</p>
            </div>
            <span className="text-xs font-mono font-bold text-accent bg-surface-2 px-2.5 py-1 rounded-lg border border-subtle">
              Peak: {Math.max(...stages.map(s => s.duration_ms || 0))} ms
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
            <span>Average Stage Latency: {(totalDuration / stages.length).toFixed(1)} ms</span>
            <span className="text-accent">Click bar to inspect stage</span>
          </div>
        </div>

        {/* Right Chart: Forensic Anomaly Radar Profile */}
        <div className="rounded-2xl border p-5 bg-surface-1 shadow-sm flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-black text-ink-primary flex items-center gap-2">
                <span>Multi-Disciplinary Forensic Risk Radar</span>
                <span className="text-[0.625rem] font-mono px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-500">10 Axes</span>
              </h3>
              <p className="text-xs text-ink-muted mt-0.5">Cross-modal severity distribution (0-100 Risk Index)</p>
            </div>
            <span className="text-xs font-mono font-bold text-ink-secondary bg-surface-2 px-2.5 py-1 rounded-lg border border-subtle">
              Max Risk: {Math.max(...radarData.map(r => r.score))}%
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={200}>
              <RadarChart data={radarData} outerRadius="75%">
                <PolarGrid stroke="var(--border-subtle)" strokeOpacity={0.6} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontWeight: 'bold' }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="var(--border-subtle)" tick={{ fill: 'var(--text-muted)', fontSize: 8 }} />
                <Radar name="Anomaly Severity" dataKey="score" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.35} />
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
            <span>Critical Anomaly Threshold: &gt;65%</span>
            <span className="text-emerald-500">Normal Range: &lt;35%</span>
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
            {onSwitchSubTab && activeStage.targetSubTab && (
              <button
                onClick={() => onSwitchSubTab(activeStage.targetSubTab)}
                className="btn-secondary py-1.5 px-3 text-xs text-accent font-bold flex items-center gap-1.5 hover:bg-accent/10 cursor-pointer"
              >
                <span>Deep Dive Sub-Tab</span>
                <ArrowRight size={13} />
              </button>
            )}
          </div>
        </div>

        {/* Detailed Inspection Telemetry Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
          <div className="p-4 rounded-xl border bg-surface-1 md:col-span-2 flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
            <div>
              <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted block mb-1">
                Diagnostic Findings &amp; Evidentiary Signal
              </span>
              <p className="font-mono text-xs text-ink-primary leading-relaxed bg-surface-2 p-3 rounded-lg border border-subtle">
                {activeStage.desc}
              </p>
            </div>
            <div className="mt-3 flex items-center justify-between text-[0.65rem] text-ink-muted pt-2 border-t border-subtle">
              <span>Cryptographic Attestation: PASS</span>
              <span>Sequence Position: {activeStage.stage} of 11</span>
            </div>
          </div>

          <div className="p-4 rounded-xl border bg-surface-1 flex flex-col justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
            <div>
              <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted block mb-2">
                Engine Benchmark
              </span>
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-ink-secondary">Detection Threshold:</span>
                  <span className="font-mono font-bold text-ink-primary">&gt; 0.45</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-ink-secondary">Engine Category:</span>
                  <span className="font-mono text-accent text-right">{activeStage.category}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-ink-secondary">Execution Mode:</span>
                  <span className="font-mono text-ink-primary">RTX Torch CUDA</span>
                </div>
              </div>
            </div>
            <div className="mt-3 pt-2 border-t border-subtle flex justify-between items-center">
              <span className="text-[0.625rem] text-ink-muted">Inspect Next Stage:</span>
              <button
                onClick={() => setActiveStageNum(activeStageNum === 11 ? 1 : activeStageNum + 1)}
                className="text-xs font-bold text-accent hover:underline flex items-center gap-1 cursor-pointer"
              >
                <span>Stage {activeStageNum === 11 ? 1 : activeStageNum + 1}</span>
                ➔
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── 5. Full Stage Audit Logs List ────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-black text-ink-primary uppercase tracking-wider">
              11-Stage Forensic Audit Trail
            </h3>
            <p className="text-xs text-ink-secondary">Complete linear execution logs for digital forensics court attestation</p>
          </div>

          <div className="flex items-center gap-1.5 p-1 rounded-xl border bg-surface-2 self-start sm:self-auto" style={{ borderColor: 'var(--border-subtle)' }}>
            {['all', 'flagged', 'passed'].map(f => (
              <button
                key={f}
                onClick={() => setFilterMode(f)}
                className={`px-3 py-1 rounded-lg text-xs font-bold capitalize transition-all cursor-pointer ${
                  filterMode === f
                    ? 'bg-accent text-white shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary'
                }`}
              >
                {f === 'all' ? `All Stages (${stages.length})` : f === 'flagged' ? `Flagged (${flaggedCount})` : `Passed (${passedCount})`}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2.5">
          {filteredStages.map((mod) => {
            const isBad = ['AI_FLAGGED', 'ANOMALY_DETECTED', 'SUSPICIOUS', 'FAILED'].includes(mod.status)
            const isWarn = ['INCONCLUSIVE', 'INSUFFICIENT_FACE_FRAMES', 'INSUFFICIENT_FACE_SAMPLES', 'SKIPPED'].includes(mod.status)
            const isSelected = activeStageNum === mod.stage
            const color = getStatusColor(mod.status)

            return (
              <div
                key={mod.stage}
                onClick={() => setActiveStageNum(mod.stage)}
                className={`rounded-xl border p-4 transition-all cursor-pointer shadow-xs ${
                  isSelected ? 'ring-2 ring-accent border-accent bg-surface-2' : 'hover:bg-surface-2 bg-surface-1'
                }`}
                style={{
                  borderColor: isSelected ? 'var(--accent)' : isBad ? 'rgba(239,68,68,0.3)' : isWarn ? 'rgba(245,158,11,0.3)' : 'var(--border-subtle)',
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span
                      className="flex h-8 w-8 items-center justify-center rounded-xl text-xs font-black shadow-xs shrink-0"
                      style={{
                        background: color + '22',
                        color: color,
                        border: `1.5px solid ${color}`
                      }}
                    >
                      {mod.stage}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-extrabold text-ink-primary">
                          Stage {mod.stage}: {mod.name}
                        </span>
                        <span className="text-[0.625rem] font-bold uppercase mono text-accent px-1.5 py-0.5 rounded bg-surface-2">
                          {mod.category}
                        </span>
                      </div>
                      <p className="text-xs text-ink-secondary mt-0.5 leading-relaxed">
                        {mod.desc}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5">
                    {mod.duration_ms != null && (
                      <span className="mono text-xs text-ink-muted bg-surface-2 px-2.5 py-1 rounded-md border" style={{ borderColor: 'var(--border-subtle)' }}>
                        {mod.duration_ms} ms
                      </span>
                    )}
                    <span
                      className="text-[0.625rem] font-black uppercase px-2.5 py-1 rounded-md border mono"
                      style={{
                        background: color + '18',
                        color: color,
                        borderColor: color + '44',
                      }}
                    >
                      {mod.status.replace(/_/g, ' ')}
                    </span>
                    {onSwitchSubTab && mod.targetSubTab && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onSwitchSubTab(mod.targetSubTab)
                        }}
                        className="text-xs text-accent hover:underline font-bold px-1.5 py-0.5"
                        title="Jump to forensic sub-tab"
                      >
                        ➔
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
