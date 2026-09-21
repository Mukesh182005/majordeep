import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, useScroll, useTransform, useSpring, AnimatePresence } from 'framer-motion'
import { Notice } from '../components/ui'
import {
  Activity, ArrowRight, CheckCircle, Copy, Cpu,
  Eye, FileText, Hash, Image as ImageIcon,
  Lock, ShieldAlert, ShieldCheck, Sparkles,
  Video as VideoIcon, Waveform, Zap,
} from '../components/ui/Icons'

// ─── Data ──────────────────────────────────────────────────────────────────
const STATS = [
  { value: '99.9%',   label: 'Detection Accuracy',      sub: '140k training samples',    icon: Zap,      color: '#3b82f6' },
  { value: '< 120ms', label: 'Inference Latency',        sub: 'CUDA GPU accelerated',     icon: Cpu,      color: '#10b981' },
  { value: '0.0011',  label: 'Equal Error Rate',         sub: 'State-of-art benchmark',   icon: Activity, color: '#8b5cf6' },
  { value: 'SHA-256', label: 'Cryptographic Attestation', sub: 'Legal chain of custody',  icon: Hash,     color: '#f59e0b' },
]

const CAPABILITIES = [
  {
    id: 'image', label: 'Image Forensics',
    icon: ImageIcon, color: '#3b82f6',
    tag: 'EfficientNet-B4 + ViT',
    desc: '28-module suite: GAN artifact detection, face-swap isolation, ELA noise analysis, CFA demosaicing, steganography scan & Grad-CAM explainability.',
    pills: ['PRNU Sensor Noise', 'CFA Demosaicing', 'ELA Calibration', 'Grad-CAM Heatmap', 'Face-Swap Detection', 'Metadata Forensics'],
    accuracy: 99,
  },
  {
    id: 'audio', label: 'Voice & Audio',
    icon: Waveform, color: '#8b5cf6',
    tag: 'SincRawNet3 + WavLM L18',
    desc: '10-engine ensemble: IAIF glottal inverse filtering, ENF power grid phase, WavLM SSL probing, conformal prediction bounding & temporal splicing.',
    pills: ['IAIF Glottal Flow', 'ENF Phase Grid', 'SSL Probing', 'Conformal Risk', 'Vocoder Signature', 'Splicing Timeline'],
    accuracy: 98,
  },
  {
    id: 'video', label: 'Video Analysis',
    icon: VideoIcon, color: '#10b981',
    tag: 'Frame Aggregator',
    desc: 'Temporal frame sampling with per-keyframe deep forensics, jitter detection, face-tracking trajectory, and inter-frame consistency analysis.',
    pills: ['Temporal Jitter', 'Multi-Face Track', 'Frame Confidence', 'Transient Flicker', 'GAN Artifacts', 'Keyframe Delta'],
    accuracy: 97,
  },
]

const PIPELINE = [
  { num: '01', phase: 'INGESTION & SEAL', title: 'Cryptographic Chain of Custody', color: '#3b82f6',
    icon: Hash, detail: 'SHA-256 · Zero Cloud Exposure · SWGDE Evidence Ledger',
    desc: 'On arrival, an immutable SHA-256 digest is computed and the file is locked in an isolated enclave. Every byte is verified before analysis begins.' },
  { num: '02', phase: 'NEURAL ATTRIBUTION', title: 'CUDA Tensor Matrix Scoring', color: '#8b5cf6',
    icon: Cpu, detail: 'EfficientNet-B4 · LCNN · WavLM · Multi-Face MTCNN',
    desc: 'High-throughput neural backbones evaluate spatial, frequency, and temporal domains. Ensemble fusion prevents single-model bias.' },
  { num: '03', phase: 'EXPLAINABLE FORENSICS', title: 'Grad-CAM Visual Attribution', color: '#f59e0b',
    icon: Eye, detail: 'Pixel-Level Heatmaps · Per-Frame Timelines · Spectral Anomalies',
    desc: 'Gradient-weighted class activation maps pinpoint the exact blending seams, eye anomalies, and spectral artifacts that drove the verdict.' },
  { num: '04', phase: 'CERTIFIED DOSSIER', title: 'Automated Forensic Report', color: '#10b981',
    icon: FileText, detail: 'Tamper-Evident PDF · Case Reference · Methodological Disclosure',
    desc: 'Findings compile into a standardized forensic dossier with hash verification, confidence distributions, and Grad-CAM attachments.' },
]

const TRUST = [
  { icon: Hash,       title: 'Cryptographic Integrity', body: 'SHA-256 fingerprints for both the source file and generated report. Independently verifiable at any time.' },
  { icon: Lock,       title: 'Local-Only Processing',   body: 'Media never leaves your server. GPU pipeline runs on-premises. One-click permanent erasure of all evidence.' },
  { icon: ShieldCheck, title: 'Calibrated Uncertainty', body: 'Borderline cases are surfaced as inconclusive — never forced into an uncertain binary verdict.' },
]

// ─── Sub-components ─────────────────────────────────────────────────────────

function LivePill() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -12, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="inline-flex items-center gap-2.5 rounded-full border px-4 py-1.5 backdrop-blur-md"
      style={{ borderColor: 'rgba(59,130,246,0.4)', background: 'var(--surface-glass)', fontSize: '0.75rem', fontWeight: 700 }}
    >
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
      </span>
      <span style={{ color: 'var(--accent)' }}>VERITAS DEEPFAKE FORENSICS</span>
      <span style={{ color: 'var(--text-muted)' }}>·</span>
      <span className="mono" style={{ color: 'var(--text-secondary)', fontSize: '0.6875rem' }}>v1.0 CUDA ACCELERATED</span>
    </motion.div>
  )
}

function StatCard({ stat, delay }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -4, scale: 1.02 }}
      className="card relative overflow-hidden"
      style={{ padding: 'clamp(1.125rem, 1.5vw, 1.625rem)' }}
    >
      {/* Color splash */}
      <div
        className="pointer-events-none absolute -right-4 -top-4 h-20 w-20 rounded-full blur-2xl"
        style={{ background: stat.color, opacity: 0.12 }}
      />
      <div className="grid h-9 w-9 place-items-center rounded-xl mb-3" style={{ background: `${stat.color}18`, color: stat.color }}>
        <stat.icon size={16} />
      </div>
      <p className="tnum font-extrabold tracking-tight text-ink-primary"
         style={{ fontSize: 'clamp(1.5rem, 2.5vw, 2.25rem)', letterSpacing: '-0.035em', lineHeight: 1 }}>
        {stat.value}
      </p>
      <p className="mt-1.5 font-semibold text-ink-primary" style={{ fontSize: 'clamp(0.75rem, 0.85vw, 0.875rem)' }}>
        {stat.label}
      </p>
      <p className="mt-0.5 text-ink-muted" style={{ fontSize: 'clamp(0.6875rem, 0.7vw, 0.8125rem)' }}>
        {stat.sub}
      </p>
    </motion.div>
  )
}

function ScannerDemo({ mousePos, onMouseMove, activeTab, setActiveTab, copiedHash, copyHash, sampleHash }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.7 }}
      onMouseMove={onMouseMove}
      className="relative overflow-hidden rounded-2xl border backdrop-blur-xl"
      style={{
        borderColor: 'rgba(59,130,246,0.25)',
        background: 'var(--surface-glass)',
        boxShadow: 'var(--shadow-xl)',
        padding: 'clamp(1.25rem, 2.5vw, 2rem)',
      }}
    >
      {/* Cursor spotlight */}
      <div
        className="pointer-events-none absolute inset-0 transition-opacity duration-300"
        style={{ background: `radial-gradient(600px circle at ${mousePos.x}px ${mousePos.y}px, rgba(59,130,246,0.08), transparent 45%)` }}
      />

      {/* Window chrome */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b pb-4" style={{ borderColor: 'var(--border-subtle)' }}>
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500/80" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/80" />
            <span className="h-3 w-3 rounded-full bg-green-500/80" />
          </div>
          <span className="mono text-[0.6875rem] font-semibold text-ink-muted">
            VERITAS // LIVE TENSOR DIAGNOSTIC · CASE: DF-20260901-8A3C21
          </span>
        </div>
        <div className="flex rounded-lg p-1 text-[0.75rem] font-semibold" style={{ background: 'var(--surface-2)' }}>
          {[['heatmap', Eye, 'Grad-CAM'], ['original', ImageIcon, 'Original']].map(([id, Icon, label]) => (
            <button key={id} onClick={() => setActiveTab(id)}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-all"
              style={activeTab === id
                ? { background: 'var(--accent)', color: '#fff' }
                : { color: 'var(--text-secondary)' }}>
              <Icon size={13} />{label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 items-center">
        {/* Heatmap visual */}
        <div className="relative overflow-hidden rounded-xl p-4" style={{ background: 'var(--surface-2)' }}>
          <div className="mx-auto relative aspect-square max-w-[260px] overflow-hidden rounded-xl border-2 shadow-lg"
               style={{ borderColor: 'rgba(59,130,246,0.5)' }}>
            <div className="h-full w-full transition-all duration-700"
                 style={{ background: activeTab === 'heatmap'
                   ? 'radial-gradient(ellipse at 48% 44%, rgba(239,68,68,0.9) 0%, rgba(245,158,11,0.8) 30%, rgba(59,130,246,0.5) 65%, rgba(15,23,42,0.97) 100%)'
                   : 'linear-gradient(160deg, #1e293b 0%, #0f172a 100%)' }}>
              {/* Wireframe overlay */}
              <div className="absolute inset-5 rounded-xl border border-dashed p-3" style={{ borderColor: 'rgba(59,130,246,0.6)' }}>
                <div className="flex items-center justify-between">
                  <span className="mono text-[0.5625rem] font-bold" style={{ color: 'var(--accent)' }}>ROI: FACE_01</span>
                  <span className="mono text-[0.5625rem] font-bold text-red-400">σ: 0.998</span>
                </div>
                <div className="mt-6 flex justify-around">
                  <span className="h-4 w-4 rounded-full border" style={{ borderColor: 'rgba(59,130,246,0.8)', background: 'rgba(59,130,246,0.1)' }} />
                  <span className="h-4 w-4 rounded-full border" style={{ borderColor: 'rgba(59,130,246,0.8)', background: 'rgba(59,130,246,0.1)' }} />
                </div>
                <div className="mx-auto mt-5 h-2.5 w-12 rounded-full border" style={{ borderColor: 'rgba(239,68,68,0.8)', background: 'rgba(239,68,68,0.2)' }} />
              </div>
            </div>
            {/* Scan line */}
            <motion.div
              animate={{ y: [0, 260, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
              className="pointer-events-none absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
              style={{ boxShadow: '0 0 10px #22d3ee' }}
            />
          </div>
          <div className="mt-3 flex justify-between px-1 text-[0.7rem]" style={{ color: 'var(--text-muted)' }}>
            <span>EfficientNet-B4 (Binary Head)</span>
            <span className="font-bold" style={{ color: 'var(--accent)' }}>CUDA: 42ms</span>
          </div>
        </div>

        {/* Verdict panel */}
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="badge font-extrabold" style={{ background: 'var(--status-crit-bg)', color: 'var(--status-critical)' }}>
                <ShieldAlert size={13} /> LIKELY MANIPULATED
              </span>
              <span className="tnum font-black text-red-500" style={{ fontSize: 'clamp(1.5rem, 3vw, 2.25rem)', letterSpacing: '-0.04em' }}>99.8%</span>
            </div>
            <h3 className="font-bold text-ink-primary" style={{ fontSize: 'clamp(1rem, 1.5vw, 1.25rem)', letterSpacing: '-0.02em' }}>
              Synthetic Face Swap Detected
            </h3>
            <p className="mt-1.5 leading-relaxed text-ink-secondary" style={{ fontSize: 'clamp(0.8125rem, 0.9vw, 0.9375rem)' }}>
              High-frequency spatial blending anomalies and warping artifacts isolated in the periorbital and jawline regions.
            </p>
          </div>

          {/* Confidence bar */}
          <div>
            <div className="flex justify-between mb-1.5" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              <span>Authentic (0.0)</span>
              <span>Synthetic (1.0)</span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full" style={{ background: 'var(--surface-3)' }}>
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: '99.8%' }}
                viewport={{ once: true }}
                transition={{ duration: 1.2, ease: 'easeOut' }}
                className="h-full rounded-full bg-gradient-to-r from-amber-500 via-rose-500 to-red-500"
              />
            </div>
          </div>

          {/* Evidence signals */}
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'GAN Artifacts', score: '0.97', color: '#ef4444' },
              { label: 'Boundary Blend', score: '0.94', color: '#f97316' },
              { label: 'PRNU Mismatch', score: '0.89', color: '#eab308' },
              { label: 'ELA Anomaly', score: '0.91', color: '#ef4444' },
            ].map(sig => (
              <div key={sig.label} className="rounded-lg px-3 py-2" style={{ background: 'var(--surface-2)' }}>
                <div className="flex items-center justify-between">
                  <span style={{ fontSize: '0.625rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{sig.label}</span>
                  <span className="tnum font-black" style={{ fontSize: '0.75rem', color: sig.color }}>{sig.score}</span>
                </div>
                <div className="mt-1.5 h-1 rounded-full overflow-hidden" style={{ background: 'var(--surface-3)' }}>
                  <div className="h-full rounded-full" style={{ width: `${parseFloat(sig.score)*100}%`, background: sig.color, opacity: 0.85 }} />
                </div>
              </div>
            ))}
          </div>

          {/* Hash box */}
          <div className="rounded-xl border p-3" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-2)' }}>
            <div className="flex items-center justify-between mb-1">
              <span style={{ fontSize: '0.625rem', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>SHA-256 Evidence Fingerprint</span>
              <button onClick={copyHash} className="flex items-center gap-1 font-bold text-accent hover:underline" style={{ fontSize: '0.6875rem' }}>
                {copiedHash ? <CheckCircle size={11} /> : <Copy size={11} />}
                {copiedHash ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <p className="mono truncate text-ink-secondary" style={{ fontSize: '0.6875rem' }}>{sampleHash}</p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function CapabilityCard({ cap, isActive, onClick, idx }) {
  const Icon = cap.icon
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: idx * 0.08 }}
      onClick={onClick}
      className="card relative overflow-hidden cursor-pointer transition-all duration-300"
      style={{
        padding: 'clamp(1.25rem, 1.75vw, 1.75rem)',
        borderColor: isActive ? cap.color : 'var(--border-subtle)',
        boxShadow: isActive ? `var(--shadow-lg), 0 0 0 2px ${cap.color}30, 0 0 40px ${cap.color}18` : 'var(--shadow-sm)',
        transform: isActive ? 'translateY(-4px)' : 'translateY(0)',
      }}
    >
      <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full blur-3xl transition-opacity duration-300"
           style={{ background: cap.color, opacity: isActive ? 0.15 : 0 }} />

      <div className="flex items-start justify-between mb-4">
        <div className="grid h-12 w-12 place-items-center rounded-2xl transition-all duration-200"
             style={{ background: isActive ? cap.color : `${cap.color}18`, color: isActive ? '#fff' : cap.color }}>
          <Icon size={22} />
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1.5 justify-end">
            <span className="tnum font-black" style={{ fontSize: 'clamp(1.375rem, 2vw, 1.875rem)', color: cap.color, letterSpacing: '-0.03em' }}>
              {cap.accuracy}%
            </span>
          </div>
          <span style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Accuracy</span>
        </div>
      </div>

      <h3 className="font-bold text-ink-primary" style={{ fontSize: 'clamp(1rem, 1.3vw, 1.1875rem)', letterSpacing: '-0.02em' }}>
        {cap.label}
      </h3>
      <div className="mt-1 mb-3 mono" style={{ fontSize: '0.6875rem', color: cap.color, fontWeight: 700 }}>
        {cap.tag}
      </div>
      <p className="leading-relaxed text-ink-secondary" style={{ fontSize: 'clamp(0.8125rem, 0.9vw, 0.9375rem)' }}>
        {cap.desc}
      </p>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {cap.pills.map(p => (
          <span key={p}
            className="rounded-full px-2.5 py-1 font-semibold transition-colors duration-200"
            style={{
              fontSize: '0.625rem',
              background: isActive ? `${cap.color}18` : 'var(--surface-2)',
              color: isActive ? cap.color : 'var(--text-muted)',
              letterSpacing: '0.02em',
            }}>
            {p}
          </span>
        ))}
      </div>

      {/* Accuracy bar */}
      <div className="mt-4 h-1 rounded-full overflow-hidden" style={{ background: 'var(--surface-3)' }}>
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${cap.accuracy}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease: 'easeOut', delay: idx * 0.1 }}
          className="h-full rounded-full"
          style={{ background: cap.color }}
        />
      </div>
    </motion.div>
  )
}

function PipelineStep({ step, idx }) {
  const Icon = step.icon
  return (
    <motion.div
      initial={{ opacity: 0, x: idx % 2 === 0 ? -20 : 20 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: '-30px' }}
      transition={{ duration: 0.6, delay: idx * 0.1 }}
      className="relative flex gap-5"
    >
      {/* Step number + connector */}
      <div className="flex flex-col items-center shrink-0">
        <div className="grid h-12 w-12 place-items-center rounded-2xl text-white font-black z-10"
             style={{ background: step.color, fontSize: '0.75rem', boxShadow: `0 4px 16px ${step.color}40` }}>
          {step.num}
        </div>
        {idx < PIPELINE.length - 1 && (
          <div className="mt-2 w-0.5 flex-1 min-h-[2.5rem]" style={{ background: `linear-gradient(to bottom, ${step.color}60, transparent)` }} />
        )}
      </div>

      {/* Content */}
      <div className="pb-8 flex-1">
        <p style={{ fontSize: '0.625rem', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', color: step.color }}>
          {step.phase}
        </p>
        <h3 className="font-bold text-ink-primary mt-0.5" style={{ fontSize: 'clamp(1rem, 1.3vw, 1.25rem)', letterSpacing: '-0.02em' }}>
          {step.title}
        </h3>
        <p className="mt-2 leading-relaxed text-ink-secondary" style={{ fontSize: 'clamp(0.8125rem, 0.9vw, 0.9375rem)' }}>
          {step.desc}
        </p>
        <div className="mono mt-3 flex items-center gap-2" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
          <Icon size={12} style={{ color: step.color }} />
          {step.detail}
        </div>
      </div>
    </motion.div>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function Landing() {
  const [activeTab, setActiveTab] = useState('heatmap')
  const [activeCap, setActiveCap] = useState('image')
  const [copiedHash, setCopiedHash] = useState(false)
  const [mousePos, setMousePos] = useState({ x: 200, y: 200 })
  const [tick, setTick] = useState(0)

  const { scrollYProgress } = useScroll()
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 80, damping: 25 })

  const sampleHash = '3a7b8e1f0c92d54e8b3a7f29104c8e76a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0'

  // Subtle blinking ticker for the live terminal feel
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 2000)
    return () => clearInterval(t)
  }, [])

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }

  const copyHash = () => {
    navigator.clipboard?.writeText(sampleHash)
    setCopiedHash(true)
    setTimeout(() => setCopiedHash(false), 1500)
  }

  return (
    <div 
      className="relative overflow-hidden cursor-investigator blueprint-bg" 
      style={{ minHeight: '100vh', paddingBottom: 'clamp(4rem, 8vw, 8rem)' }}
      onMouseMove={handleMouseMove}
    >

      {/* ── Ambient background ─────────────────────────────────── */}
      <div className="pointer-events-none fixed inset-0 -z-20 overflow-hidden">
        <motion.div
          className="absolute top-[20vh] left-[10vw] h-[600px] w-[600px] rounded-full blur-[160px] opacity-[0.05]"
          style={{ background: 'var(--accent)' }}
        />
        <div className="absolute top-[60vh] -right-40 h-[500px] w-[500px] rounded-full blur-[120px] opacity-[0.03]"
             style={{ background: 'var(--status-critical)' }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

        {/* ══════════════════════════════ HERO ══════════════════════════════ */}
        <section className="relative flex flex-col items-center justify-center flex-1" style={{ minHeight: '80vh' }}>
          
          {/* Minimalist Crosshair Target */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className="relative mb-12"
          >
            <div className="w-16 h-16 border border-accent rounded-full opacity-30 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"></div>
            <div className="w-32 h-32 border border-accent rounded-full opacity-10 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"></div>
            <div className="w-px h-8 bg-accent absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[200%]"></div>
            <div className="w-px h-8 bg-accent absolute top-1/2 left-1/2 -translate-x-1/2 translate-y-[100%]"></div>
            <div className="h-px w-8 bg-accent absolute top-1/2 left-1/2 -translate-y-1/2 -translate-x-[200%]"></div>
            <div className="h-px w-8 bg-accent absolute top-1/2 left-1/2 -translate-y-1/2 translate-x-[100%]"></div>
            <div className="w-2 h-2 bg-accent rounded-full absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-ping"></div>
            <div className="w-1 h-1 bg-accent rounded-full absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"></div>
          </motion.div>

          <LivePill />

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto mt-7 font-black text-ink-primary uppercase tracking-[0.1em]"
            style={{ fontSize: 'clamp(1rem, 2vw, 1.25rem)' }}
          >
            Acoustic & Optical Forensic Sandbox
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto mt-4 text-ink-secondary font-mono"
            style={{ fontSize: '0.75rem', maxWidth: '54ch', lineHeight: 1.65, textAlign: 'center' }}
          >
            [ SYNCING SECURE ENCLAVE... ]<br/>
            Waiting for multi-modal target data to initiate SHA-256 stream.
          </motion.p>

          {/* Ghost CTA Button */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.34 }}
            className="mt-10"
          >
            <Link
              to="/analyse"
              className="group relative inline-flex items-center gap-3 overflow-hidden font-mono uppercase tracking-[0.1em] text-accent transition-all duration-300 hover:text-white"
              style={{
                padding: '1rem 2rem',
                fontSize: '0.75rem',
                fontWeight: 700,
                border: '1px solid var(--accent)',
                backgroundColor: 'transparent'
              }}
            >
              <div className="absolute inset-0 w-0 bg-accent transition-all duration-300 ease-out group-hover:w-full z-0" />
              <span className="relative z-10">Initialize Sequence</span>
              <ArrowRight size={14} className="relative z-10 transition-transform group-hover:translate-x-1" />
            </Link>
          </motion.div>
        </section>

        {/* Global Coordinate Tracker */}
        <div className="fixed bottom-6 right-6 font-mono text-[0.625rem] text-accent opacity-60 z-50 pointer-events-none">
          LOC: [ {Math.round(mousePos.x).toString().padStart(4, '0')}, {Math.round(mousePos.y).toString().padStart(4, '0')} ]
        </div>

        {/* Stats row */}
        <div className="mx-auto mt-14 grid max-w-5xl grid-cols-2 gap-4 sm:grid-cols-4 px-4">
          {STATS.map((s, i) => <StatCard key={s.label} stat={s} delay={0.45 + i * 0.08} />)}
        </div>

        {/* ══════════════════════════ LIVE SCANNER DEMO ══════════════════════ */}
        <section className="mx-auto w-full max-w-6xl">
          <div className="mb-8 text-center">
            <span className="badge badge-neutral mb-3">Live Tensor Diagnostic</span>
            <h2 className="font-extrabold text-ink-primary"
                style={{ fontSize: 'clamp(1.75rem, 3vw, 3rem)', letterSpacing: '-0.035em' }}>
              See the Forensics in Action
            </h2>
            <p className="mx-auto mt-2.5 text-ink-secondary"
               style={{ fontSize: 'clamp(0.875rem, 1vw, 1.0625rem)', maxWidth: '52ch' }}>
              A real-time forensic session showing Grad-CAM attention overlays, evidence signal scoring, and SHA-256 attestation.
            </p>
          </div>
          <ScannerDemo
            mousePos={mousePos}
            onMouseMove={handleMouseMove}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            copiedHash={copiedHash}
            copyHash={copyHash}
            sampleHash={sampleHash}
          />
        </section>

        {/* ══════════════════════════ CAPABILITIES ═══════════════════════════ */}
        <section className="mx-auto w-full max-w-6xl">
          <div className="mb-10 text-center">
            <span className="badge badge-neutral mb-3">Dedicated Neural Engines</span>
            <h2 className="font-extrabold text-ink-primary"
                style={{ fontSize: 'clamp(1.75rem, 3vw, 3rem)', letterSpacing: '-0.035em' }}>
              Specialized Multi-Modal Detection
            </h2>
            <p className="mx-auto mt-2.5 text-ink-secondary"
               style={{ fontSize: 'clamp(0.875rem, 1vw, 1.0625rem)', maxWidth: '52ch' }}>
              Different media formats leave different manipulation footprints. Veritas applies tailored neural networks to each.
            </p>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {CAPABILITIES.map((cap, i) => (
              <CapabilityCard
                key={cap.id} cap={cap} idx={i}
                isActive={activeCap === cap.id}
                onClick={() => setActiveCap(cap.id)}
              />
            ))}
          </div>
        </section>

        {/* ══════════════════════════ PIPELINE ════════════════════════════════ */}
        <section className="mx-auto w-full max-w-6xl">
          <div className="grid gap-14 lg:grid-cols-2 lg:gap-20 items-start">
            {/* Left: heading */}
            <div className="lg:sticky lg:top-24">
              <span className="badge badge-neutral mb-4">The Methodology</span>
              <h2 className="font-extrabold text-ink-primary"
                  style={{ fontSize: 'clamp(1.75rem, 3vw, 3rem)', letterSpacing: '-0.035em' }}>
                4-Stage Forensic{' '}
                <span style={{ background: 'var(--grad-accent)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
                  Verification
                </span>
              </h2>
              <p className="mt-4 leading-relaxed text-ink-secondary"
                 style={{ fontSize: 'clamp(0.875rem, 1vw, 1.0625rem)', maxWidth: '42ch' }}>
                From raw media ingestion to court-admissible attestation — every step is deterministic, logged, and independently verifiable.
              </p>

              {/* Terminal readout */}
              <div className="mt-8 rounded-2xl border overflow-hidden"
                   style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-2)' }}>
                <div className="flex items-center gap-2 px-4 py-2.5 border-b" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-3)' }}>
                  <div className="flex gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
                    <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" />
                    <span className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
                  </div>
                  <span className="mono text-[0.625rem] font-semibold text-ink-muted ml-1">FORENSICS.LOG</span>
                </div>
                <div className="p-4 space-y-1.5 mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                  {[
                    { t: '17:48:02.091', msg: 'Stage 1 complete — SHA256: 3a7b8e1f…', c: '#10b981' },
                    { t: '17:48:02.334', msg: 'Stage 2 — EfficientNet-B4 inference', c: '#3b82f6' },
                    { t: '17:48:02.476', msg: 'Stage 3 — Grad-CAM maps generated', c: '#f59e0b' },
                    { t: '17:48:02.601', msg: 'Stage 4 — Risk fusion: 0.998 CRITICAL', c: '#ef4444' },
                  ].map((line, i) => (
                    <div key={i} className="flex gap-3">
                      <span style={{ color: 'var(--text-muted)', opacity: 0.6 }}>{line.t}</span>
                      <span style={{ color: line.c }}>{line.msg}</span>
                    </div>
                  ))}
                  <div className="flex items-center gap-2 pt-1">
                    <span style={{ color: '#10b981' }}>▶</span>
                    <span style={{ color: '#3b82f6' }}>VERDICT: AI_GENERATED</span>
                    <span className={tick % 2 === 0 ? 'opacity-100' : 'opacity-0'} style={{ color: 'var(--text-muted)', transition: 'opacity 0.2s' }}>█</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: pipeline steps */}
            <div className="pt-2">
              {PIPELINE.map((step, i) => (
                <PipelineStep key={step.num} step={step} idx={i} />
              ))}
            </div>
          </div>
        </section>

        {/* ══════════════════════════ TRUST PILLARS ═══════════════════════════ */}
        <section className="mx-auto w-full max-w-6xl">
          <div className="grid gap-5 sm:grid-cols-3">
            {TRUST.map((t, i) => (
              <motion.div
                key={t.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                whileHover={{ y: -4 }}
                className="card flex gap-4 transition-all hover:shadow-lg hover:border-accent/40"
                style={{ padding: 'clamp(1.25rem, 1.75vw, 1.75rem)' }}
              >
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl"
                      style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                  <t.icon size={20} />
                </span>
                <div>
                  <h4 className="font-bold text-ink-primary" style={{ fontSize: 'clamp(0.875rem, 1vw, 1rem)' }}>
                    {t.title}
                  </h4>
                  <p className="mt-1.5 leading-relaxed text-ink-secondary" style={{ fontSize: 'clamp(0.8125rem, 0.85vw, 0.9375rem)' }}>
                    {t.body}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </section>


        {/* ══════════════════════════ LEGAL NOTICE ════════════════════════════ */}
        <div className="mx-auto w-full max-w-6xl">
          <Notice tone="warn" title="Evidentiary Notice & Standards">
            Deepfake detectors produce probabilistic scores based on trained statistical signatures.
            While Veritas utilizes state-of-the-art architectures (99.9% benchmark accuracy),
            severe compression or very low resolution may affect results. For formal legal proceedings,
            verification by a court-certified digital forensics examiner is recommended.
          </Notice>
        </div>
      </div>
    </div>
  )
}
