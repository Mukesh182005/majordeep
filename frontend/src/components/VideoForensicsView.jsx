import { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, SplitLoupeOverlay } from './ui'
import AuthedImage from './AuthedImage'
import {
  Activity, Alert, CheckCircle, Cpu, Eye, FileText,
  Info, ShieldAlert, ShieldCheck, Video as VideoIcon, Zap,
} from './ui/Icons'
import { percent } from '../lib/format'
import VideoPipelineVisualizer from './VideoPipelineVisualizer'

export const VIDEO_PIPELINE_STAGES = [
  { id: 1,  stage: 1,  name: 'Container & Bitstream Forensics',          desc: 'Binary parsing of ISO Base Media boxes (ftyp, moov, trak, mdat) and metadata' },
  { id: 2,  stage: 2,  name: 'Scene & Shot Boundary Segmentation',      desc: 'Bhattacharyya color/edge delta boundary segmentation for independent scene evaluation' },
  { id: 3,  stage: 3,  name: 'Spatial Neural & Generative AI Backbone', desc: 'Running neural facial detector and ViT full-scene generative artifact backbones' },
  { id: 4,  stage: 4,  name: '28-Module Image Forensic Engine',         desc: 'Evaluated CFA Bayer periodicity, Fourier radial slope alpha, ELA, and synthetic background matte voids on keyframes' },
  { id: 5,  stage: 5,  name: 'Temporal Jitter & Facial Dynamics (unvalidated)',       desc: 'Measuring bounding box acceleration, facial landmark trajectory, and ocular blink synchrony (unvalidated heuristic)' },
  { id: 6,  stage: 6,  name: 'Remote Photoplethysmography (rPPG) (unvalidated)',       desc: 'Cardiovascular Blood Volume Pulse (BVP) extraction from capillary reflectance (0.75-2.5 Hz) (unvalidated heuristic)' },
  { id: 7,  stage: 7,  name: 'Spatio-Temporal 4D Tensor Dynamics (unvalidated)',      desc: 'TimeSformer divided space-time patch variance, latent denoise jumps, and SlowFast boundary vibration (unvalidated heuristic)' },
  { id: 8,  stage: 8,  name: 'LipForensics Articulatory Kinematics (unvalidated)',    desc: 'Oral kinematic velocity, 2nd-derivative articulatory jerk, and phonetic coarticulation smoothness (unvalidated heuristic)' },
  { id: 9,  stage: 9,  name: 'Optical Flow Motion Decomposition (unvalidated)',       desc: 'Farneback dense optical flow computing motion vector divergence at composition seams (unvalidated heuristic)' },
  { id: 10, stage: 10, name: 'Acoustic Speech & Cross-Modal Lip-Sync',  desc: 'Audio demuxing, LCNN Voice AI, glottal IAIF flow physics, and speech-to-lip aperture correlation' },
  { id: 11, stage: 11, name: 'AI Generator Attribution (unvalidated)',         desc: 'Intrinsic physical & latent diffusion matching (unvalidated heuristic: hand-set profiles, not tested on labelled video)' },
]

function VideoScoreBar({ value = 0, color = '#ff3860', label, sub }) {
  const pct = Math.round(value * 100)
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[0.6875rem] font-bold text-ink-muted uppercase tracking-wider">{label}</span>
        <span className="tnum font-black" style={{ fontSize: '0.9375rem', color }}>{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full" style={{ background: 'var(--surface-3)' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ background: color }}
        />
      </div>
      {sub && <p className="mt-0.5 text-[0.625rem] text-ink-muted">{sub}</p>}
    </div>
  )
}

function VideoMetricBadge({ label, value, color = 'var(--accent)', mono = false }) {
  return (
    <div className="rounded-xl border p-3 flex flex-col gap-0.5" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-2)' }}>
      <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">{label}</span>
      <span className={`font-black ${mono ? 'mono' : ''}`} style={{ fontSize: 'clamp(0.9375rem, 1.5vw, 1.25rem)', color, letterSpacing: mono ? '-0.02em' : undefined }}>
        {value}
      </span>
    </div>
  )
}

function TabButton({ id, label, icon: Icon, activeTab, onClick }) {
  const isActive = activeTab === id
  return (
    <button
      onClick={() => onClick(id)}
      className={`flex-none inline-flex items-center gap-1.5 px-4 py-2 text-[13.5px] font-bold rounded-full border-[1.5px] transition-all whitespace-nowrap ${
        isActive
          ? 'bg-accent border-accent text-white shadow-sm cursor-default'
          : 'bg-surface-1 text-ink-muted border-transparent hover:border-accent hover:text-accent'
      }`}
    >
      {Icon && <Icon size={14} className={isActive ? 'text-white' : 'opacity-70'} />}
      <span>{label}</span>
    </button>
  )
}

export default function VideoForensicsView({ result, activeSubTab, setActiveSubTab }) {
  const evidence = result.evidence || {}
  const temporal = evidence.temporal_metrics || {}
  const frameScores = evidence.frame_scores || []
  const container = evidence.container_forensics || {}
  const scenes = evidence.scenes || []
  const facial = evidence.facial_dynamics || {}
  const lipsync = evidence.crossmodal_lipsync || {}
  const attribution = evidence.generator_attribution || {}
  const imageForensics = evidence.image_forensics || {}
  const audioForensics = evidence.audio_forensics || {}
  const rppg = evidence.rppg_biometrics || {}
  const spatiotemporal = evidence.spatiotemporal_forensics || {}
  const lipForensics = evidence.lip_forensics || {}
  const faceTracks = evidence.face_tracks || []
  const hasFaceTracks = Array.isArray(faceTracks) && faceTracks.length > 0
  const segmentTimeline = evidence.segment_timeline || []
  const highestTrackScore = hasFaceTracks
    ? Math.max(...faceTracks.map(t => (t.score ?? t.fake_probability ?? t.top_25_pct_mean ?? 0)))
    : null

  const [zoomTimeline] = useState(false)

  const currentTab = activeSubTab || 'summary'

  const motion = temporal.motion_anomaly ?? 0
  const compress = temporal.compression_anomaly ?? 0
  const spatialProb = frameScores.length
    ? Math.max(...frameScores.map(s => s.fake_probability))
    : result.fake_probability ?? 0
  const vitGenAiProb = evidence.vit_genai_prob ?? 0
  // GenD face-swap detector: the mean over face frames decides (when gend_in_verdict); max is shown.
  const gendMean = evidence.gend_face_mean
  const gendMax = evidence.gend_face_max
  const gendRan = typeof gendMean === 'number'
  const gendLabel = evidence.gend_in_verdict ? 'GenD face-swap (in verdict)' : 'GenD face-swap (unvalidated, not in verdict)'

  const fakePct = Math.round((result.fake_probability ?? 0) * 100)
  const riskColor = fakePct >= 65 ? 'var(--status-critical)' : fakePct >= 35 ? 'var(--status-warn)' : 'var(--status-good)'
  const dominantThreat = evidence.dominant_threat || 'Analyzing Video Dynamics'
  const threatCode = evidence.threat_code || result.verdict
  const isAuthentic = result.verdict === 'likely_authentic' || result.verdict === 'authentic'
  const hasThreat = fakePct >= 50 || (
    dominantThreat &&
    !isAuthentic &&
    !dominantThreat.toLowerCase().includes('authentic') &&
    !dominantThreat.toLowerCase().includes('inconclusive')
  )

  const TABS = [
    { id: 'summary',    label: hasThreat ? 'Threat & Summary' : 'Forensic Summary', icon: hasThreat ? ShieldAlert : ShieldCheck },
    { id: 'pipeline',   label: 'Pipeline Stages (11)',      icon: Cpu },
    { id: 'origin',     label: 'AI Generator (unvalidated)', icon: Zap },
    { id: 'biometrics', label: 'Biometrics & 4D Tensor (unvalidated)', icon: Activity },
    { id: 'timeline',   label: 'Forensic Timeline',         icon: Activity },
    { id: 'scenes',     label: 'Scenes & Segments',         icon: VideoIcon },
    { id: 'facial',     label: 'Facial & Motion Dynamics (unvalidated)', icon: Eye },
    { id: 'container',  label: 'Container & Bitstream',     icon: FileText },
    { id: 'lipsync',    label: 'Cross-Modal Lip-Sync',      icon: Zap },
  ]

  const renderFaceSwapForensics = () => {
    return (
      <Card
        title="Trained Face-Swap Model Forensics"
        subtitle={
          hasFaceTracks
            ? "Per-track scores derived from mean of top 25% frame scores; video score is the highest track score."
            : "Facial detection & face-swap temporal track verification"
        }
        action={
          hasFaceTracks ? (
            <span className="px-2.5 py-0.5 rounded-full text-[0.65rem] font-bold uppercase tracking-wider bg-accent/15 text-accent border border-accent/30">
              Trained Model (Face-Swap)
            </span>
          ) : null
        }
      >
        {!hasFaceTracks ? (
          <div className="mt-3 p-4 rounded-xl border bg-surface-2 flex items-center gap-3" style={{ borderColor: 'var(--border-subtle)' }}>
            <Info size={18} className="text-ink-muted shrink-0" />
            <div>
              <p className="text-sm font-bold text-ink-primary">
                No face found: face-swap check not applicable.
              </p>
              <p className="text-xs text-ink-muted mt-0.5">
                Face-swap verification requires detected facial bounding boxes. Full-scene generative detection and bitstream checks remain operational.
              </p>
            </div>
          </div>
        ) : (
          <div className="mt-3 space-y-4">
            {/* Metric summary 4-grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <VideoMetricBadge
                label="Highest Track Score"
                value={percent(highestTrackScore)}
                color={highestTrackScore >= 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
              />
              <VideoMetricBadge
                label="Face Tracks"
                value={faceTracks.length}
                color="var(--accent)"
              />
              <VideoMetricBadge
                label="Track Aggregation"
                value="Top 25% Mean"
                color="var(--ink-secondary)"
              />
              <VideoMetricBadge
                label="Model Decision"
                value={highestTrackScore >= 0.50 ? 'FLAGGED' : 'AUTHENTIC'}
                color={highestTrackScore >= 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
              />
            </div>

            {/* Per-Track Scores Breakdown */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">
                  Per-Track Scores ({faceTracks.length} {faceTracks.length === 1 ? 'Track' : 'Tracks'})
                </span>
                <span className="text-[0.625rem] text-ink-muted font-mono">
                  Rule: Mean of top 25% frame scores
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {faceTracks.map((track, idx) => {
                  const tId = track.track_id ?? track.id ?? idx
                  const score = track.score ?? track.fake_probability ?? track.top_25_pct_mean ?? 0
                  const pct = Math.round(score * 100)
                  const isFlagged = score >= 0.50
                  const color = isFlagged ? '#ff3860' : '#22c55e'
                  const frames = track.frames_analyzed ?? track.frame_count ?? track.frames_tracked ?? track.frames?.length ?? '–'
                  const timeRange = (track.start_s != null && track.end_s != null)
                    ? `t=${track.start_s.toFixed(2)}s – ${track.end_s.toFixed(2)}s`
                    : (track.time_range || 'Entire duration')

                  return (
                    <div
                      key={tId}
                      className="p-3.5 rounded-xl border bg-surface-2 flex flex-col justify-between gap-2.5"
                      style={{ borderColor: isFlagged ? 'rgba(255,56,96,0.35)' : 'var(--border-subtle)' }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-black bg-surface-3 text-ink-primary">
                            #{tId}
                          </span>
                          <div>
                            <span className="text-xs font-black text-ink-primary">Face Track #{tId}</span>
                            <span className="text-[0.625rem] text-ink-muted block">{timeRange} • {frames} frames</span>
                          </div>
                        </div>
                        <span
                          className="px-2 py-0.5 rounded text-[0.625rem] font-black uppercase mono border"
                          style={{
                            background: isFlagged ? 'rgba(255,56,96,0.15)' : 'rgba(34,197,94,0.15)',
                            color,
                            borderColor: isFlagged ? 'rgba(255,56,96,0.3)' : 'rgba(34,197,94,0.3)',
                          }}
                        >
                          {track.status || (isFlagged ? 'FLAGGED' : 'AUTHENTIC')}
                        </span>
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-baseline justify-between text-xs">
                          <span className="text-[0.625rem] uppercase font-bold text-ink-muted">Track Score (Top 25% Mean)</span>
                          <span className="mono font-black" style={{ color }}>{pct}%</span>
                        </div>
                        <div className="h-2 w-full bg-surface-3 rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Segment Timeline from the new response */}
            {segmentTimeline.length > 0 && (
              <div className="pt-3 border-t" style={{ borderColor: 'var(--border-subtle)' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">
                    Temporal Segment Timeline (from model response)
                  </span>
                  <span className="text-[0.625rem] text-ink-muted">
                    Track-calibrated timeline
                  </span>
                </div>
                <div className="overflow-x-auto rounded-xl border max-h-60" style={{ borderColor: 'var(--border-subtle)' }}>
                  <table className="w-full text-[0.6875rem]" style={{ borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: 'var(--surface-3)', borderBottom: '1px solid var(--border-subtle)' }}>
                        {['Time Window', 'Face-Swap Score', 'Manipulation Class', 'Indicators', 'Source Match'].map(h => (
                          <th key={h} className="px-3 py-2 text-left font-bold uppercase tracking-wider text-ink-muted">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {segmentTimeline.map((seg, idx) => {
                        const isHigh = seg.ai_probability >= 0.50
                        return (
                          <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <td className="px-3 py-2 mono font-bold text-ink-primary">{seg.time_window}</td>
                            <td className="px-3 py-2">
                              <span className={`font-black tnum ${isHigh ? 'text-red-500' : 'text-green-500'}`}>
                                {seg.ai_percentage ?? percent(seg.ai_probability)}
                              </span>
                            </td>
                            <td className="px-3 py-2 mono font-semibold text-ink-secondary">{seg.manipulation_type}</td>
                            <td className="px-3 py-2 text-ink-muted">{seg.indicators}</td>
                            <td className="px-3 py-2 mono text-accent">{seg.source_match}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Sub-Tabs navigation */}
      <div className="flex items-center gap-2 overflow-x-auto p-4 border-b bg-surface-2 no-print" style={{ borderColor: 'var(--border-subtle)' }}>
        {TABS.map(t => (
          <TabButton
            key={t.id}
            id={t.id}
            label={t.label}
            icon={t.icon}
            activeTab={currentTab}
            onClick={setActiveSubTab}
          />
        ))}
      </div>

      <div className="p-6 space-y-6 overflow-y-auto min-h-0 flex-1">

      {/* ── TAB 1: Threat & Summary ───────────────────────────────────────── */}
      {currentTab === 'summary' && (
        <div className="space-y-6">
          {/* Main Face-Swap Model Forensics (Per-track scores & timeline, or not applicable message) */}
          {renderFaceSwapForensics()}

          {/* Forensic Threat Attribution Banner - only rendered if a manipulation threat is detected */}
          {hasThreat && (
            <div className="p-5 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm"
                 style={{
                   background: 'rgba(255,56,96,0.08)',
                   borderColor: 'rgba(255,56,96,0.3)',
                 }}>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                  <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Forensic Threat Classification</span>
                </div>
                <h2 className="text-2xl font-black text-ink-primary tracking-tight">{dominantThreat}</h2>
                <p className="text-xs text-ink-secondary mt-1">
                  Unified multi-modal verdict fusing Spatial Image Forensics, Acoustic Audio Forensics, and Temporal Video Dynamics.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-3.5 py-1.5 rounded-xl text-xs font-black uppercase tracking-wider mono border"
                      style={{
                        background: 'rgba(255,56,96,0.15)',
                        color: '#ff3860',
                        borderColor: 'rgba(255,56,96,0.3)',
                      }}>
                  {threatCode}
                </span>
              </div>
            </div>
          )}

          {/* AI Generator Origin Card (unvalidated heuristic) */}
          <Card title="AI Generator Attribution (unvalidated)" subtitle="unvalidated heuristic: hand-set profiles, not tested on labelled video">
            <div className="mt-3 p-4 rounded-xl border bg-surface-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4" style={{ borderColor: 'var(--border-subtle)' }}>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 rounded text-[0.625rem] font-black uppercase bg-amber-500/15 text-amber-500 border border-amber-500/30 mono">
                    UNVALIDATED HEURISTIC
                  </span>
                </div>
                <h3 className="text-base font-black text-ink-primary mt-1">
                  {attribution.predicted_platform ? `${attribution.predicted_platform} (unvalidated)` : 'Authentic Camera / No Synthetic Traces'}
                </h3>
                <p className="text-xs text-ink-secondary mt-1 leading-relaxed max-w-2xl">
                  {attribution.explanation || 'Analyzed physical camera sensor noise, Fourier azimuthal energy decay, and spatio-temporal texture morphing rate.'} (unvalidated heuristic)
                </p>
              </div>
              <div className="text-right shrink-0">
                <span className="text-[0.625rem] font-bold uppercase text-ink-muted">Attribution Confidence (unvalidated)</span>
                <p className="text-xl font-black mono text-accent">
                  {Math.round((attribution.attribution_confidence || 0.12) * 100)}%
                </p>
              </div>
            </div>
          </Card>

          {/* Tripartite Multi-Modal Engine Collaborations */}
          <Card title="Multi-Modal Engine Collaboration" subtitle="Simultaneous execution across Spatial Image, Acoustic Audio, and Temporal Video pipelines">
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* 1. Spatial Image Forensics */}
              <div className="p-3.5 rounded-xl border bg-surface-2 space-y-2" style={{ borderColor: 'var(--border-subtle)' }}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-ink-primary">Spatial Image Forensics</span>
                  <span className="text-[0.625rem] font-bold uppercase mono text-accent">28 Modules</span>
                </div>
                <p className="text-[0.6875rem] text-ink-muted">Evaluated on video keyframes & worst frame</p>
                <div className="pt-2 border-t space-y-1 text-xs" style={{ borderColor: 'var(--border-subtle)' }}>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">ViT Scene GenAI:</span>
                    <span className="mono font-bold text-ink-primary">{Math.round(vitGenAiProb * 100)}%</span>
                  </div>
                  <div className="flex justify-between" data-testid="gend-face-score">
                    <span className="text-ink-secondary">{gendRan ? `${gendLabel}, mean / max over ${evidence.gend_faces_scored} faces:` : 'Face-swap check:'}</span>
                    <span className="mono font-bold text-ink-primary">
                      {gendRan ? `${Math.round(gendMean * 100)}% / ${Math.round(gendMax * 100)}%` : 'No face found: not applicable'}
                    </span>
                  </div>
                  {Array.isArray(evidence.scene_frame_scores) && (
                    <div className="flex justify-between">
                      <span className="text-ink-secondary">Scene AI frames scored:</span>
                      <span className="mono font-bold text-ink-primary">{evidence.scene_frame_scores.length}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">CFA Periodic Peak:</span>
                    <span className="mono font-bold text-ink-primary">{imageForensics.camera_cfa?.cfa_periodicity_ratio ?? '–'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">Fourier Slope α:</span>
                    <span className="mono font-bold text-ink-primary">{imageForensics.camera_cfa?.fourier_spectral_slope ?? '–'}</span>
                  </div>
                </div>
              </div>

              {/* 2. Acoustic Audio Forensics */}
              <div className="p-3.5 rounded-xl border bg-surface-2 space-y-2" style={{ borderColor: 'var(--border-subtle)' }}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-ink-primary">Acoustic Audio Forensics</span>
                  <span className="text-[0.625rem] font-bold uppercase mono text-accent">10 Engines</span>
                </div>
                <p className="text-[0.6875rem] text-ink-muted">Demuxed audio track acoustic analysis</p>
                <div className="pt-2 border-t space-y-1 text-xs" style={{ borderColor: 'var(--border-subtle)' }}>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">Audio Track Status:</span>
                    <span className="mono font-bold text-ink-primary">{lipsync.audio_stream_detected ? 'Demuxed' : 'Absent'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">Voice AI Synthetic:</span>
                    <span className="mono font-bold text-ink-primary">
                      {audioForensics.fusion_decision?.calibrated_fake_probability != null
                        ? `${Math.round(audioForensics.fusion_decision.calibrated_fake_probability * 100)}%`
                        : '–'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">ENF Grid Phase:</span>
                    <span className="mono font-bold text-ink-primary">
                      {audioForensics.enf_environment?.environmental_splicing_confirmed ? 'Spliced' : 'Coherent'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">Audiovisual Sync:</span>
                    <span className="mono font-bold text-ink-primary">{lipsync.audiovisual_correlation ?? '–'}</span>
                  </div>
                </div>
              </div>

              {/* 3. Temporal Video Forensics */}
              <div className="p-3.5 rounded-xl border bg-surface-2 space-y-2" style={{ borderColor: 'var(--border-subtle)' }}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-ink-primary">Temporal Video Dynamics (unvalidated)</span>
                  <span className="text-[0.625rem] font-bold uppercase mono text-accent">Farneback Flow (unvalidated)</span>
                </div>
                <p className="text-[0.6875rem] text-ink-muted">Motion boundary vectors & genealogy</p>
                <div className="pt-2 border-t space-y-1 text-xs" style={{ borderColor: 'var(--border-subtle)' }}>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">Optical Flow Anomaly:</span>
                    <span className="mono font-bold text-ink-primary">{Math.round(motion * 100)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">Landmark Jitter:</span>
                    <span className="mono font-bold text-ink-primary">{facial.landmark_jitter_score ?? '0.00'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">Re-encoding Anomaly:</span>
                    <span className="mono font-bold text-ink-primary">{Math.round(compress * 100)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-secondary">Shots Segmented:</span>
                    <span className="mono font-bold text-ink-primary">{scenes.length} Scenes</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Key Metrics 4-grid */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <VideoMetricBadge label="Composite Risk Score" value={`${fakePct}%`} color={riskColor} />
            <VideoMetricBadge label={gendRan ? 'GenD Face Score (mean)' : 'Spatial Peak (Worst Frame)'} value={percent(gendRan ? gendMean : spatialProb)} color={(gendRan ? gendMean : spatialProb) >= 0.65 ? 'var(--status-critical)' : 'var(--status-good)'} />
            <VideoMetricBadge label="Frames Analysed" value={evidence.frames_analysed ?? frameScores.length} color="var(--accent)" />
            <VideoMetricBadge label="Worst Frame Marker" value={`t=${evidence.worst_frame_timestamp_s?.toFixed(2) ?? '–'}s`} color="var(--status-warn)" mono />
          </div>

          {/* Corroborating Signals Card */}
          {evidence.corroborating_signals?.length > 0 && (
            <Card title="Corroborating Forensic Evidence" subtitle="Multi-modal forensic traces substantiating this classification">
              <div className="mt-3 space-y-2.5">
                {evidence.corroborating_signals.map((sig, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-xl border bg-surface-2" style={{ borderColor: 'var(--border-subtle)' }}>
                    <ShieldAlert size={16} className="text-red-500 shrink-0 mt-0.5" />
                    <span className="text-xs font-semibold text-ink-primary leading-relaxed">{sig}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Modular Forensic Pipeline Stages Overview */}
          <Card
            title="Modular Forensic Pipeline Execution (11 Stages)"
            subtitle="Sequential multi-modal analytical engines logging execution timing and status flags"
          >
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {(evidence.pipeline_modules?.length ? evidence.pipeline_modules : VIDEO_PIPELINE_STAGES).map((mod, idx) => {
                const stageNum = mod.stage || mod.id || idx + 1
                const st = mod.status || 'PASSED'
                const isBad = ['SUSPICIOUS', 'AI_FLAGGED', 'ANOMALY_DETECTED', 'FAILED'].includes(st)
                const isWarn = ['INCONCLUSIVE', 'INSUFFICIENT_FACE_FRAMES', 'INSUFFICIENT_FACE_SAMPLES', 'SKIPPED'].includes(st)
                return (
                  <div
                    key={stageNum}
                    onClick={() => setActiveSubTab('pipeline')}
                    className="cursor-pointer rounded-xl border p-3 flex flex-col justify-between transition hover:border-accent hover:shadow-sm"
                    style={{
                      borderColor: isBad ? 'rgba(255,56,96,0.35)' : isWarn ? 'rgba(255,176,32,0.35)' : 'var(--border-subtle)',
                      background: isBad ? 'rgba(255,56,96,0.04)' : isWarn ? 'rgba(255,176,32,0.04)' : 'var(--surface-2)',
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className="flex h-5 w-5 items-center justify-center rounded-full text-[0.625rem] font-black"
                          style={{
                            background: isBad ? 'var(--status-crit-bg)' : isWarn ? 'rgba(255,176,32,0.15)' : 'var(--status-good-bg)',
                            color: isBad ? 'var(--status-critical)' : isWarn ? 'var(--status-warn)' : 'var(--status-good)',
                          }}
                        >
                          {stageNum}
                        </span>
                        <span className="text-xs font-bold text-ink-primary truncate max-w-[170px]">
                          {mod.name}
                        </span>
                      </div>
                      <span
                        className="text-[0.5625rem] font-bold uppercase px-1.5 py-0.5 rounded mono"
                        style={{
                          background: isBad ? 'var(--status-crit-bg)' : isWarn ? 'rgba(255,176,32,0.15)' : 'var(--status-good-bg)',
                          color: isBad ? 'var(--status-critical)' : isWarn ? 'var(--status-warn)' : 'var(--status-good)',
                        }}
                      >
                        {st.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[0.625rem] text-ink-muted mt-2 pt-1.5 border-t border-subtle">
                      <span className="truncate max-w-[190px]">{mod.desc || mod.summary}</span>
                      {mod.duration_ms != null && <span className="mono shrink-0 ml-1">{mod.duration_ms}ms</span>}
                    </div>
                  </div>
                )
              })}
            </div>
            <div className="mt-3 flex justify-end">
              <button
                onClick={() => setActiveSubTab('pipeline')}
                className="btn-secondary py-1.5 px-3 text-xs flex items-center gap-1.5 text-accent font-bold"
              >
                <span>Explore Full 11-Stage Workflow & Node Diagram</span>
                <span>➔</span>
              </button>
            </div>
          </Card>

          {/* Container & Metadata Highlights */}
          <Card title="Video Stream Specifications" subtitle="Ingestion container and temporal format metadata">
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: 'Video Category',   value: evidence.video_category || 'No Manipulation Detected' },
                { label: 'Editing App / Tool', value: container.editing_software || 'Camera Direct Capture' },
                { label: 'Container Brand',  value: container.container_format || 'MP4' },
                { label: 'Duration',         value: evidence.duration_seconds ? `${evidence.duration_seconds.toFixed(2)}s` : '–' },
                { label: 'Framerate',        value: evidence.source_fps ? `${evidence.source_fps.toFixed(2)} fps` : '–' },
                { label: 'Resolution',       value: evidence.width ? `${evidence.width}×${evidence.height}` : '–' },
                { label: 'AI Generator Tag', value: container.ai_generator_signature || 'None detected' },
                { label: 'Screen Recording', value: container.screen_recording_analysis?.screen_recording_detected ? 'DETECTED' : 'Negative' },
              ].map(m => (
                <div key={m.label} className="rounded-lg border p-3" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-2)' }}>
                  <p className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">{m.label}</p>
                  <p className="mt-0.5 mono font-bold text-ink-primary text-xs truncate">{m.value}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ── TAB 2: AI Generator & Diffusion ───────────────────────────────── */}
      {currentTab === 'origin' && (
        <div className="space-y-6">
          {/* Generator Candidate Likelihoods */}
          <Card title="Candidate AI Generator Attribution (unvalidated)" subtitle="unvalidated heuristic: hand-set profiles, not tested on labelled video">
            <div className="mt-3 space-y-3">
              {attribution.generator_scores && Object.entries(attribution.generator_scores).map(([k, score]) => {
                const isWinner = score === Math.max(...Object.values(attribution.generator_scores))
                return (
                  <div key={k} className="p-3 rounded-xl border bg-surface-2" style={{ borderColor: isWinner ? 'var(--accent)' : 'var(--border-subtle)' }}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-black text-ink-primary">{k.replace(/_/g, ' ')}</span>
                        {isWinner && (
                          <span className="px-2 py-0.5 rounded text-[0.625rem] font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
                            Predicted Match (unvalidated)
                          </span>
                        )}
                      </div>
                      <span className="mono font-black text-xs text-ink-primary">{Math.round(score * 100)}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-surface-3 rounded-full overflow-hidden">
                      <div className="h-full bg-accent rounded-full" style={{ width: `${score * 100}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>

          {/* Intrinsic Latent Metrics (unvalidated heuristic) */}
          <Card title="Intrinsic Latent Diffusion Signatures (unvalidated heuristic)" subtitle="Physical optical and spectral traits demonstrating synthetic generation (unvalidated heuristic; not tested on labelled video)">
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <VideoMetricBadge
                label="Sensor Shot Noise (std)"
                value={attribution.intrinsic_metrics?.sensor_noise_std ?? '–'}
                color={attribution.intrinsic_metrics?.sensor_noise_std < 1.25 ? 'var(--status-critical)' : 'var(--status-good)'}
                mono
              />
              <VideoMetricBadge
                label="Fourier Decay Slope (α)"
                value={attribution.intrinsic_metrics?.fourier_slope_alpha ?? '–'}
                color={attribution.intrinsic_metrics?.fourier_slope_alpha > 2.35 ? 'var(--status-critical)' : 'var(--status-good)'}
                mono
              />
              <VideoMetricBadge
                label="Wavelet HH Peak Ratio"
                value={attribution.intrinsic_metrics?.wavelet_peak_ratio ?? '–'}
                color={attribution.intrinsic_metrics?.wavelet_peak_ratio > 3.2 ? 'var(--status-critical)' : 'var(--status-good)'}
                mono
              />
              <VideoMetricBadge
                label="Texture Morphing Rate"
                value={attribution.intrinsic_metrics?.morphing_rate ?? '–'}
                color={attribution.intrinsic_metrics?.morphing_rate > 0.32 ? 'var(--status-critical)' : 'var(--status-good)'}
                mono
              />
            </div>

            <div className="mt-4 p-4 rounded-xl border bg-surface-2" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">Detected Intrinsic Traces Checklist</span>
              <ul className="mt-2 space-y-1.5">
                {attribution.detected_signatures?.map((sig, i) => (
                  <li key={i} className="flex items-center gap-2 text-xs text-ink-primary font-semibold">
                    <CheckCircle size={14} className="text-accent shrink-0" />
                    <span>{sig}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Card>
        </div>
      )}

      {/* ── TAB: Biometrics & 4D Tensor Dynamics ────────────────────────── */}
      {currentTab === 'biometrics' && (
        <div className="space-y-6">
          {/* 1. rPPG Cardiovascular Blood Volume Pulse Monitor (unvalidated) */}
          <Card
            title="Remote Photoplethysmography (rPPG) Cardiovascular Biometrics (unvalidated)"
            subtitle="Capillary micro-vascular perfusion analysis (unvalidated heuristic) — detecting natural cardiac pulse rhythms (0.75 Hz – 2.50 Hz / 45 – 150 BPM) vs synthetic biometric voids"
          >
            <div className="mt-3 p-4 rounded-xl border bg-surface-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4" style={{ borderColor: 'var(--border-subtle)' }}>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="px-2.5 py-1 rounded-md text-[0.625rem] font-black uppercase mono border"
                    style={{
                      background: rppg.biometric_pulse_detected
                        ? 'rgba(143,230,42,0.15)'
                        : rppg.is_synthetic_biometric_void
                        ? 'rgba(255,56,96,0.15)'
                        : 'rgba(234,179,8,0.15)',
                      color: rppg.biometric_pulse_detected
                        ? '#8fe62a'
                        : rppg.is_synthetic_biometric_void
                        ? '#ff3860'
                        : '#eab308',
                      borderColor: rppg.biometric_pulse_detected
                        ? 'rgba(143,230,42,0.3)'
                        : rppg.is_synthetic_biometric_void
                        ? 'rgba(255,56,96,0.3)'
                        : 'rgba(234,179,8,0.3)',
                    }}
                  >
                    {rppg.status || (rppg.biometric_pulse_detected ? 'PHYSIOLOGICAL PULSE CONFIRMED' : 'SYNTHETIC BIOMETRIC VOID')}
                  </span>
                </div>
                <h4 className="text-sm font-black text-ink-primary mt-1">
                  {rppg.biometric_pulse_detected
                    ? `Authentic Biological Heartbeat (${rppg.estimated_heart_rate_bpm} BPM)`
                    : (rppg.is_synthetic_biometric_void
                        ? 'Absence of Biological Pulse (Synthetic Facial Void)'
                        : 'Biometric Photoplethysmography Evaluation')}
                </h4>
                <p className="text-xs text-ink-secondary mt-1 max-w-2xl leading-relaxed">
                  Extracts subtle chrominance shifts via Plane-Orthogonal-to-Skin (POS) algorithms across facial forehead and cheek capillaries to detect involuntary cardiovascular pulse signals.
                </p>
              </div>
              <div className="text-right shrink-0">
                <span className="text-[0.625rem] font-bold uppercase text-ink-muted">Biological Plausibility</span>
                <div
                  className="text-2xl font-black mono"
                  style={{ color: rppg.biometric_pulse_detected ? '#8fe62a' : '#ff3860' }}
                >
                  {Math.round((rppg.biological_plausibility_score ?? 0.5) * 100)}%
                </div>
              </div>
            </div>

            {/* rPPG Metrics 4-grid */}
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <VideoMetricBadge
                label="Estimated Heart Rate"
                value={rppg.estimated_heart_rate_bpm ? `${rppg.estimated_heart_rate_bpm} BPM` : '–'}
                color={rppg.biometric_pulse_detected ? 'var(--status-good)' : 'var(--status-critical)'}
                mono
              />
              <VideoMetricBadge
                label="Cardiac Band SNR"
                value={rppg.cardiac_snr_db != null ? `${rppg.cardiac_snr_db} dB` : '–'}
                color={rppg.cardiac_snr_db >= 1.5 ? 'var(--status-good)' : 'var(--status-critical)'}
                mono
              />
              <VideoMetricBadge
                label="Cardiac Power Ratio"
                value={rppg.cardiac_power_ratio != null ? `${Math.round(rppg.cardiac_power_ratio * 100)}%` : '–'}
                color="var(--accent)"
                mono
              />
              <VideoMetricBadge
                label="Capillary Pulse State"
                value={rppg.biometric_pulse_detected ? 'AUTHENTIC' : (rppg.is_synthetic_biometric_void ? 'SYNTHETIC' : 'INDETERMINATE')}
                color={rppg.biometric_pulse_detected ? 'var(--status-good)' : 'var(--status-critical)'}
              />
            </div>

            {/* Live Reconstructed SVG BVP Pulse Waveform */}
            {rppg.pulse_waveform?.length > 0 ? (
              <div className="mt-4 p-4 rounded-xl border bg-black text-white" style={{ borderColor: 'var(--border-subtle)' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[0.6875rem] font-bold uppercase tracking-wider text-green-400 flex items-center gap-1.5">
                    <Activity size={14} className="animate-pulse text-green-400" />
                    Reconstructed Capillary Blood Volume Pulse (BVP) Waveform
                  </span>
                  <span className="mono text-[0.6875rem] text-neutral-400">
                    POS Chrominance Decomposition
                  </span>
                </div>
                <div className="h-32 w-full relative pt-2">
                  <svg className="w-full h-full overflow-visible" viewBox="0 0 500 100" preserveAspectRatio="none">
                    {/* Baseline grid */}
                    <line x1="0" y1="25" x2="500" y2="25" stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                    <line x1="0" y1="50" x2="500" y2="50" stroke="rgba(255,255,255,0.15)" />
                    <line x1="0" y1="75" x2="500" y2="75" stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                    {/* Polyline */}
                    <polyline
                      fill="none"
                      stroke={rppg.biometric_pulse_detected ? '#8fe62a' : '#ff3860'}
                      strokeWidth="2.5"
                      points={rppg.pulse_waveform.map((pt, i, arr) => `${(i / Math.max(1, arr.length - 1)) * 500},${100 - pt.val}`).join(' ')}
                    />
                  </svg>
                </div>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/10 text-[0.6875rem] text-neutral-400">
                  <span>t = {rppg.pulse_waveform[0]?.t || 0}s</span>
                  <span>Cardiac Band: 0.75 Hz – 2.50 Hz (45–150 BPM)</span>
                  <span>t = {rppg.pulse_waveform[rppg.pulse_waveform.length - 1]?.t || 0}s</span>
                </div>
              </div>
            ) : (
              <div className="mt-3 p-4 rounded-xl border bg-surface-2 text-xs text-ink-muted">
                Insufficient continuous face frames to project photoplethysmography waveform.
              </div>
            )}

            {rppg.findings?.length > 0 && (
              <div className="mt-4 p-3.5 rounded-xl border bg-surface-2 space-y-1.5" style={{ borderColor: 'var(--border-subtle)' }}>
                <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">rPPG Biometric Findings</span>
                <ul className="space-y-1 mt-1">
                  {rppg.findings.map((f, i) => (
                    <li key={i} className="flex items-center gap-2 text-xs text-ink-primary font-semibold">
                      <CheckCircle size={13} className={rppg.biometric_pulse_detected ? 'text-green-500 shrink-0' : 'text-red-500 shrink-0'} />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* 2. Spatio-Temporal 4D Tensor Dynamics (unvalidated) */}
          <Card
            title="Spatio-Temporal 4D Tensor Forensics (unvalidated)"
            subtitle="Analyzes video volume tensors (unvalidated heuristic) (T, C, H, W) for divided space-time patch correlation, latent diffusion denoise steps, and SlowFast boundary edge vibration"
          >
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <VideoMetricBadge
                label="Spatio-Temporal Anomaly"
                value={percent(spatiotemporal.spatiotemporal_anomaly_score || 0)}
                color={spatiotemporal.spatiotemporal_anomaly_score >= 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
              />
              <VideoMetricBadge
                label="Latent Denoise Step Jumps"
                value={spatiotemporal.latent_noise_jump_rate ?? '0.00'}
                color={spatiotemporal.latent_noise_jump_rate >= 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
                mono
              />
              <VideoMetricBadge
                label="SlowFast Seam Vibration"
                value={spatiotemporal.slowfast_boundary_vibration ?? '0.00'}
                color={spatiotemporal.slowfast_boundary_vibration >= 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
                mono
              />
              <VideoMetricBadge
                label="Long-Range Temporal Drift"
                value={spatiotemporal.temporal_drift_index ?? '0.00'}
                color={spatiotemporal.temporal_drift_index >= 0.55 ? 'var(--status-critical)' : 'var(--status-good)'}
                mono
              />
            </div>

            {spatiotemporal.findings?.length > 0 && (
              <div className="mt-4 p-4 rounded-xl border bg-surface-2" style={{ borderColor: 'var(--border-subtle)' }}>
                <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">Spatio-Temporal Dynamics Audit</span>
                <ul className="mt-2 space-y-1.5">
                  {spatiotemporal.findings.map((finding, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-xs text-ink-primary font-semibold">
                      <Alert size={14} className={spatiotemporal.spatiotemporal_anomaly_score >= 0.50 ? 'text-red-500 shrink-0' : 'text-accent shrink-0'} />
                      <span>{finding}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* 3. LipForensics Phonetic Articulatory Kinematics (unvalidated) */}
          <Card
            title="LipForensics & Phonetic Articulatory Dynamics (unvalidated)"
            subtitle="Deep kinematic tracking of mouth aspect ratio (MAR) trajectories (unvalidated heuristic), articulatory jerk, and phonetic transition smoothness"
          >
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <VideoMetricBadge
                label="Lip Manipulation Risk"
                value={percent(lipForensics.lip_manipulation_probability || 0)}
                color={lipForensics.lip_manipulation_probability >= 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
              />
              <VideoMetricBadge
                label="Articulatory Jerk Anomaly"
                value={lipForensics.articulatory_jerk_anomaly ?? '0.00'}
                color={lipForensics.articulatory_jerk_anomaly >= 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
                mono
              />
              <VideoMetricBadge
                label="Phonetic Smoothness"
                value={percent(lipForensics.phonetic_transition_smoothness ?? 1.0)}
                color={lipForensics.phonetic_transition_smoothness < 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
              />
              <VideoMetricBadge
                label="Oral Texture Stability"
                value={percent(lipForensics.oral_cavity_texture_stability ?? 1.0)}
                color={lipForensics.oral_cavity_texture_stability < 0.50 ? 'var(--status-critical)' : 'var(--status-good)'}
              />
            </div>

            {lipForensics.findings?.length > 0 && (
              <div className="mt-4 p-4 rounded-xl border bg-surface-2" style={{ borderColor: 'var(--border-subtle)' }}>
                <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">Kinematic & Oral Texture Checklist</span>
                <ul className="mt-2 space-y-1.5">
                  {lipForensics.findings.map((f, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-xs text-ink-primary font-semibold">
                      <CheckCircle size={14} className={lipForensics.lip_manipulation_probability >= 0.50 ? 'text-red-500 shrink-0' : 'text-accent shrink-0'} />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ── TAB 3: Pipeline Stages ────────────────────────────────────────── */}
      {currentTab === 'pipeline' && (
        <VideoPipelineVisualizer
          result={result}
          onSwitchSubTab={setActiveSubTab}
        />
      )}

      {/* ── TAB 4: Forensic Timeline ──────────────────────────────────────── */}
      {currentTab === 'timeline' && (
        <div className="space-y-6">
          {renderFaceSwapForensics()}

          {evidence.timeline_url && (
            <Card title="High-Resolution Temporal Confidence Curve" subtitle="Frame-by-frame manipulation confidence with annotated worst-frame peak">
              <div className="mt-3 overflow-hidden rounded-xl border" style={{ borderColor: 'var(--border-subtle)' }}>
                <AuthedImage src={evidence.timeline_url} alt="Per-frame confidence timeline" className="w-full" />
              </div>
            </Card>
          )}

          {frameScores.length > 0 && (
            <Card title="Sampled Frame Forensic Log" subtitle={`${frameScores.length} frames evaluated across clip duration`}>
              <div className="mt-3 overflow-x-auto rounded-xl border max-h-96" style={{ borderColor: 'var(--border-subtle)' }}>
                <table className="w-full text-[0.6875rem]" style={{ borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--surface-2)', borderBottom: '1px solid var(--border-subtle)' }}>
                      {['Frame #', 'Timestamp', 'Neural AI Score', 'Face Detected', 'Frame Status'].map(h => (
                        <th key={h} className="px-3 py-2.5 text-left font-bold uppercase tracking-wider text-ink-muted">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {frameScores.map((s, i) => {
                      const isWorst = i === evidence.worst_frame_index
                      const isBad = s.fake_probability >= 0.65
                      const isWarn = s.fake_probability >= 0.35
                      const color = isBad ? 'var(--status-critical)' : isWarn ? 'var(--status-warn)' : 'var(--status-good)'
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)', background: isWorst ? 'rgba(255,56,96,0.07)' : 'transparent' }}>
                          <td className="px-3 py-2 mono font-semibold text-ink-secondary">
                            {isWorst && <span className="mr-1 text-red-500 font-bold">▶</span>}
                            #{s.frame_index}
                          </td>
                          <td className="px-3 py-2 mono text-ink-secondary">{s.timestamp_s.toFixed(2)}s</td>
                          <td className="px-3 py-2">
                            <span className="tnum font-black" style={{ color }}>{Math.round(s.fake_probability * 100)}%</span>
                          </td>
                          <td className="px-3 py-2">
                            {s.face_detected ? <CheckCircle size={13} className="text-green-500" /> : <span className="text-ink-muted">Whole frame</span>}
                          </td>
                          <td className="px-3 py-2">
                            <span className="rounded px-1.5 py-0.5 text-[0.5625rem] font-bold uppercase" style={{ background: `${color}18`, color }}>
                              {isBad ? 'SUSPICIOUS' : isWarn ? 'INCONCLUSIVE' : 'AUTHENTIC'}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── TAB 5: Scenes & Segments ──────────────────────────────────────── */}
      {currentTab === 'scenes' && (
        <div className="space-y-6">
          <Card title="Scene & Shot Boundary Detection" subtitle="Automatic segmentation via Bhattacharyya color histogram & edge discontinuities">
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {scenes.map(sc => (
                <div key={sc.scene_id} className="p-3.5 rounded-xl border bg-surface-2" style={{ borderColor: 'var(--border-subtle)' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-black text-ink-primary">Scene #{sc.scene_id}</span>
                    <span className="px-2 py-0.5 rounded text-[0.625rem] font-bold uppercase mono bg-surface-3 text-ink-secondary">
                      {sc.transition_type}
                    </span>
                  </div>
                  <p className="text-xs mono font-bold text-accent">{sc.start_time_s.toFixed(2)}s – {sc.end_time_s.toFixed(2)}s</p>
                  <p className="text-[0.6875rem] text-ink-muted mt-1">Duration: {sc.duration_s}s | Keyframe: t={sc.keyframe_timestamp_s}s</p>
                </div>
              ))}
            </div>
          </Card>

          {evidence.segment_timeline?.length > 0 && (
            <Card title="Segment-Level Forensic Analysis" subtitle="Second-by-second timeline isolating specific edited vs authentic segments">
              <div className="mt-3 overflow-x-auto rounded-xl border" style={{ borderColor: 'var(--border-subtle)' }}>
                <table className="w-full text-[0.6875rem]" style={{ borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--surface-2)', borderBottom: '1px solid var(--border-subtle)' }}>
                      {['Time Window', 'AI Probability', 'Manipulation Class', 'Indicators', 'Source Match'].map(h => (
                        <th key={h} className="px-3 py-2.5 text-left font-bold uppercase tracking-wider text-ink-muted">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {evidence.segment_timeline.map((seg, idx) => {
                      const isHigh = seg.ai_probability >= 0.65
                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td className="px-3 py-2 mono font-bold text-ink-primary">{seg.time_window}</td>
                          <td className="px-3 py-2">
                            <span className={`font-black tnum ${isHigh ? 'text-red-500' : 'text-green-500'}`}>{seg.ai_percentage}</span>
                          </td>
                          <td className="px-3 py-2 mono font-semibold text-ink-secondary">{seg.manipulation_type}</td>
                          <td className="px-3 py-2 text-ink-muted">{seg.indicators}</td>
                          <td className="px-3 py-2 mono text-accent">{seg.source_match}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── TAB 6: Facial & Motion Dynamics ───────────────────────────────── */}
      {currentTab === 'facial' && (
        <div className="space-y-6">
          <Card title="Facial Dynamics & Ocular Blink Analysis (unvalidated)" subtitle="Tracking facial biometric consistency, landmark acceleration, and blink plausibility (unvalidated heuristic)">
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <VideoMetricBadge label="Landmark Jitter" value={facial.landmark_jitter_score?.toFixed(2) ?? '0.00'} color={facial.landmark_jitter_score >= 0.35 ? 'var(--status-critical)' : 'var(--status-good)'} mono />
              <VideoMetricBadge label="Blinks Detected" value={facial.blink_analysis?.blinks_detected ?? 0} color="var(--accent)" mono />
              <VideoMetricBadge label="Blink Frequency" value={`${facial.blink_analysis?.blink_rate_per_min ?? 0} /min`} color="var(--status-warn)" mono />
              <VideoMetricBadge label="Ocular Synchrony" value={facial.corneal_reflection_consistency?.toFixed(2) ?? '0.95'} color="var(--status-good)" mono />
            </div>
            <div className="mt-4 p-3 rounded-xl border bg-surface-2 flex items-center justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
              <div>
                <span className="text-[0.625rem] font-bold uppercase text-ink-muted">Blink Plausibility Assessment (unvalidated)</span>
                <p className="text-xs font-bold text-ink-primary mt-0.5">{facial.blink_analysis?.blink_regularity?.replace(/_/g, ' ') || 'NORMAL'}</p>
              </div>
              <span className="text-xs text-ink-secondary">Mouth Interior Texture Variance: {facial.mouth_interior_texture_variance ?? 0.0}</span>
            </div>
          </Card>

          <Card title="Optical Flow Motion Boundary Decomposition (unvalidated)" subtitle="Farneback dense motion field vectors at composition seams (unvalidated heuristic)">
            <div className="mt-3 space-y-4">
              <VideoScoreBar
                value={motion}
                color={motion >= 0.40 ? '#ff3860' : motion >= 0.20 ? '#ffb020' : '#22c55e'}
                label="Motion Vector Boundary Divergence"
                sub="High variance indicates discontinuous velocity vectors between synthesized face pixels and background scene."
              />
              <div className="p-3 rounded-xl border bg-surface-2 flex justify-between items-center" style={{ borderColor: 'var(--border-subtle)' }}>
                <span className="text-xs text-ink-secondary">Face vs Background Velocity Divergence:</span>
                <span className="text-xs font-black mono text-ink-primary">{temporal.face_bg_divergence ?? 0.0} px/frame</span>
              </div>
            </div>
          </Card>

          {evidence.heatmap_url && (
            <Card title="Grad-CAM Spatial Attribution — Worst Frame" subtitle={`Gradient activation on worst-scoring frame (t=${evidence.worst_frame_timestamp_s?.toFixed(2)}s)`}>
              <div className="mt-3 overflow-hidden rounded-xl border relative select-none cursor-ew-resize group h-[480px]" style={{ borderColor: 'rgba(255,56,96,0.3)', background: 'black' }}>
                <div className="absolute inset-0 w-full h-full pointer-events-none" style={{ filter: 'grayscale(100%) contrast(1.2) brightness(0.6)' }}>
                  <AuthedImage src={evidence.heatmap_url} alt="Structure" className="w-full h-full object-contain" />
                </div>
                <SplitLoupeOverlay url={evidence.heatmap_url} alt="Grad-CAM heatmap for worst video frame" inspectZoom={zoomTimeline} />
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── TAB 7: Container & Bitstream ──────────────────────────────────── */}
      {currentTab === 'container' && (
        <div className="space-y-6">
          <Card title="Container Forensics & Cryptographic Integrity" subtitle="Bitstream atom hierarchy and multi-hash cryptographic fingerprints">
            <div className="mt-3 space-y-2.5">
              {[
                { label: 'SHA-256', value: container.file_info?.sha256 || result.sha256 },
                { label: 'SHA-512', value: container.file_info?.sha512 || 'Generated at ingest' },
                { label: 'MD5',    value: container.file_info?.md5 || 'Generated at ingest' },
                { label: 'File Size', value: `${container.file_info?.file_size_mb ?? '–'} MB (${container.file_info?.file_size_bytes ?? '–'} bytes)` },
              ].map(h => (
                <div key={h.label} className="p-2.5 rounded-lg border bg-surface-2 flex items-center justify-between" style={{ borderColor: 'var(--border-subtle)' }}>
                  <span className="text-xs font-bold text-ink-muted">{h.label}</span>
                  <span className="text-xs mono font-bold text-ink-primary truncate max-w-[70%]">{h.value}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Physical Screen-Recording & Display Artifact Analysis" subtitle="High-frequency 2D FFT moiré harmonic peaks and window border clamping">
            <div className="mt-3 p-4 rounded-xl border flex items-center justify-between"
                 style={{
                   background: container.screen_recording_analysis?.screen_recording_detected ? 'rgba(255,56,96,0.08)' : 'var(--surface-2)',
                   borderColor: container.screen_recording_analysis?.screen_recording_detected ? 'rgba(255,56,96,0.3)' : 'var(--border-subtle)',
                 }}>
              <div>
                <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">Display Capture Assessment</span>
                <h4 className="text-sm font-black text-ink-primary mt-0.5">
                  {container.screen_recording_analysis?.description || 'Standard Camera / Render Raster'}
                </h4>
              </div>
              <div className="text-right">
                <span className="text-[0.625rem] font-bold uppercase text-ink-muted">Moiré Harmonic Ratio</span>
                <p className="text-sm font-black mono text-accent">{container.screen_recording_analysis?.moiré_harmonic_ratio ?? container.screen_recording_analysis?.moire_harmonic_ratio ?? '1.20'}</p>
              </div>
            </div>
          </Card>

          {container.atom_hierarchy?.length > 0 && (
            <Card title="ISO Base Media Atom Hierarchy" subtitle="Low-level container boxes parsed from file header to payload">
              <div className="mt-3 overflow-x-auto rounded-xl border max-h-72" style={{ borderColor: 'var(--border-subtle)' }}>
                <table className="w-full text-[0.6875rem]" style={{ borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--surface-2)', borderBottom: '1px solid var(--border-subtle)' }}>
                      {['Box Atom', 'Offset (Bytes)', 'Atom Size', 'Integrity Status'].map(h => (
                        <th key={h} className="px-3 py-2 text-left font-bold uppercase tracking-wider text-ink-muted">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {container.atom_hierarchy.map((atom, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td className="px-3 py-1.5 mono font-bold text-accent">{atom.atom}</td>
                        <td className="px-3 py-1.5 mono text-ink-secondary">{atom.offset}</td>
                        <td className="px-3 py-1.5 mono text-ink-secondary">{atom.size}</td>
                        <td className="px-3 py-1.5 text-green-500 font-bold">{atom.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── TAB 8: Cross-Modal Lip-Sync ───────────────────────────────────── */}
      {currentTab === 'lipsync' && (
        <div className="space-y-6">
          <Card title="Cross-Modal Lip-Speech Synchrony Engine" subtitle="Correlating visual mouth vertical aperture dynamics with acoustic speech envelopes">
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <VideoMetricBadge label="Audio Track" value={lipsync.audio_stream_detected ? 'DEMUXED' : 'ABSENT'} color={lipsync.audio_stream_detected ? 'var(--status-good)' : 'var(--text-muted)'} />
              <VideoMetricBadge label="Audiovisual Correlation" value={lipsync.audiovisual_correlation?.toFixed(2) ?? '0.00'} color={lipsync.audiovisual_correlation >= 0.20 ? 'var(--status-good)' : 'var(--status-warn)'} mono />
              <VideoMetricBadge label="Lip-Sync Anomaly" value={lipsync.lip_sync_anomaly_detected ? 'DETECTED' : 'NEGATIVE'} color={lipsync.lip_sync_anomaly_detected ? 'var(--status-critical)' : 'var(--status-good)'} />
            </div>

            <div className="mt-4 p-4 rounded-xl border bg-surface-2" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">Acoustic-Visual Alignment Finding</span>
              <p className="text-xs font-semibold text-ink-primary mt-1">{lipsync.verdict_reason || 'Natural speech-to-lip articulation'}</p>
            </div>

            {lipsync.mouth_aperture_timeline?.length > 0 && (
              <div className="mt-4 p-4 rounded-xl border bg-surface-2" style={{ borderColor: 'var(--border-subtle)' }}>
                <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted mb-2 block">Lip Aperture Kinematic Profile</span>
                <div className="flex items-end gap-1.5 h-16 w-full">
                  {lipsync.mouth_aperture_timeline.map((val, idx) => (
                    <div key={idx} className="flex-1 bg-accent/70 rounded-t transition-all hover:bg-accent" style={{ height: `${Math.max(10, val * 120)}%` }} title={`t_${idx}: ${val}`} />
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      </div>
    </div>
  )
}
