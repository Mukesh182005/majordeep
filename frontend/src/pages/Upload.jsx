import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { formatBytes } from '../lib/format'
import { useAuth } from '../lib/useAuth'
import { Card, Notice } from '../components/ui'
import { ArrowRight, MEDIA_ICON, Spinner, Upload as UploadIcon } from '../components/ui/Icons'

// ── Icons for media panels ────────────────────────────────────────────────
function ImageIcon({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <polyline points="21,15 16,10 5,21" />
    </svg>
  )
}

function AudioIcon({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  )
}

function VideoIcon({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="23,7 16,12 23,17 23,7" />
      <rect x="1" y="5" width="15" height="14" rx="2" />
    </svg>
  )
}

function WaveformBars() {
  return (
    <div className="waveform-bars mx-auto mb-1">
      {[...Array(12)].map((_, i) => (
        <div key={i} className="waveform-bar" />
      ))}
    </div>
  )
}

// ── Media panel categories ───────────────────────────────────────────────
const MEDIA_PANELS = [
  {
    id: 'image',
    label: 'Image Forensics',
    subLabel: 'JPG · PNG · WEBP · HEIC · AVIF · BMP · TIFF',
    description: '28-module forensic suite: ELA, CFA, face-swap, metadata, steganography & Grad-CAM',
    icon: ImageIcon,
    accentVar: '--accent',
    glowColor: 'rgba(42,120,214,0.3)',
    extensions: ['.jpg','.jpeg','.png','.webp','.bmp','.avif','.heic','.heif','.tiff','.tif','.gif','.ico','.jfif'],
    bgPattern: `radial-gradient(circle at 80% 50%, rgba(42,120,214,0.06) 0%, transparent 60%)`,
    chipColor: '#2a78d6',
  },
  {
    id: 'audio',
    label: 'Voice & Audio',
    subLabel: 'WAV · MP3 · FLAC · OGG · M4A · AAC · OPUS',
    description: '10-engine analysis: IAIF glottal flow, ENF grid, SSL probing & conformal risk',
    icon: AudioIcon,
    accentVar: '--purple',
    glowColor: 'rgba(124,58,237,0.3)',
    extensions: ['.wav','.mp3','.flac','.ogg','.m4a','.aac','.wma','.opus','.aiff','.alac'],
    bgPattern: `radial-gradient(circle at 80% 50%, rgba(124,58,237,0.07) 0%, transparent 60%)`,
    chipColor: '#7c3aed',
  },
  {
    id: 'video',
    label: 'Video Analysis',
    subLabel: 'MP4 · MOV · AVI · MKV · WEBM · FLV',
    description: 'Temporal frame aggregation across 8 sampled frames with full per-frame forensics',
    icon: VideoIcon,
    accentVar: '--emerald',
    glowColor: 'rgba(5,150,105,0.3)',
    extensions: ['.mp4','.mov','.avi','.mkv','.webm','.flv','.wmv','.m4v','.ts','.3gp'],
    bgPattern: `radial-gradient(circle at 80% 50%, rgba(5,150,105,0.07) 0%, transparent 60%)`,
    chipColor: '#059669',
  },
]

function detectPanelFromFile(file) {
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  return MEDIA_PANELS.find(p => p.extensions.includes(ext)) || null
}

const KIND_BY_EXTENSION = (limits) => {
  const map = {}
  Object.entries(limits?.allowed_extensions || {}).forEach(([kind, list]) =>
    list.forEach((ext) => { map[ext] = kind }))
  return map
}

export default function UploadPage() {
  const [limits, setLimits] = useState(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [activePanel, setActivePanel] = useState(null) // 'image'|'audio'|'video'
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState('idle')
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const navigate = useNavigate()
  const { user } = useAuth()

  useEffect(() => {
    api.limits().then(setLimits).catch(() => setLimits(null))
  }, [])

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  const allExtensions = limits
    ? Object.values(limits.allowed_extensions).flat()
    : MEDIA_PANELS.flatMap(p => p.extensions)

  function validate(candidate) {
    const suffix = candidate.name.slice(candidate.name.lastIndexOf('.')).toLowerCase()
    if (!allExtensions.includes(suffix))
      return `Unsupported file type "${suffix || 'unknown'}".`
    if (limits && candidate.size > limits.max_upload_mb * 1024 * 1024)
      return `File is ${formatBytes(candidate.size)}; limit is ${limits.max_upload_mb} MB.`
    return null
  }

  function choose(candidate) {
    if (!candidate) return
    const problem = validate(candidate)
    setError(problem)
    if (problem) { setFile(null); setPreview(null); setActivePanel(null); return }
    setFile(candidate)
    setPreview(candidate.type.startsWith('image/') ? URL.createObjectURL(candidate) : null)
    const detected = detectPanelFromFile(candidate)
    if (detected) setActivePanel(detected.id)
  }

  async function submit() {
    if (!file) return
    setError(null)
    setPhase('uploading')
    setProgress(0)
    try {
      const job = await api.upload(file, setProgress)
      navigate(`/jobs/${job.id}`)
    } catch (err) {
      setError(err.message)
      setPhase('idle')
    }
  }

  const activePanelDef = MEDIA_PANELS.find(p => p.id === activePanel)

  return (
    <div className="mx-auto max-w-3xl animate-in space-y-8">

      {/* ── Header ── */}
      <div>
        <div className="flex items-center gap-3 mb-3">
          <span
            className="badge"
            style={{ background: 'var(--accent-soft)', color: 'var(--accent)', border: '1px solid var(--border-glow)' }}
          >
            Forensic Analysis
          </span>
        </div>
        <h1
          className="font-extrabold tracking-tight text-ink-primary font-mono uppercase"
          style={{ fontSize: 'clamp(1.5rem, 2.5vw, 2rem)', letterSpacing: '-0.02em' }}
        >
          Engage Forensic Pipeline
        </h1>
        <p className="mt-2 leading-relaxed text-ink-secondary" style={{ fontSize: 'clamp(0.875rem, 1vw, 1rem)' }}>
          Initiate multi-modal deepfake detection. Media is hashed (SHA-256) during the streaming write and preserved immutable for chain-of-custody cryptographic attestation.
        </p>
      </div>

      {/* ── 3 Media Type Panels ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {MEDIA_PANELS.map((panel) => {
          const Icon = panel.icon
          const isActive = activePanel === panel.id
          return (
            <button
              key={panel.id}
              id={`panel-${panel.id}`}
              className={`media-panel text-left corner-bracket ${isActive ? 'active' : ''}`}
              style={isActive ? { boxShadow: `var(--shadow-lg), 0 0 32px ${panel.glowColor}`, borderColor: `var(${panel.accentVar})`, background: `var(--surface-glass)` } : {}}
              onClick={() => {
                setActivePanel(panel.id)
                inputRef.current?.click()
              }}
            >
              {/* Background pattern */}
              <div
                className="pointer-events-none absolute inset-0 rounded-[inherit]"
                style={{ background: isActive ? panel.bgPattern : 'none' }}
              />

              {/* Icon */}
              <div
                className="relative mb-4 grid h-14 w-14 place-items-center rounded-2xl mx-auto transition-transform duration-200"
                style={{
                  background: isActive ? `var(${panel.accentVar})` : 'var(--surface-2)',
                  color: isActive ? '#fff' : `var(${panel.accentVar})`,
                  boxShadow: isActive ? `0 4px 16px ${panel.glowColor}` : 'none',
                  transform: isActive ? 'scale(1.05)' : 'scale(1)',
                }}
              >
                {panel.id === 'audio' && isActive
                  ? <WaveformBars />
                  : <Icon size={26} />}
              </div>

              {/* Label */}
              <p className="relative font-bold text-ink-primary" style={{ fontSize: 'clamp(0.875rem, 1.2vw, 1rem)', letterSpacing: '-0.02em' }}>
                {panel.label}
              </p>
              <p className="relative mt-1 text-ink-muted mono" style={{ fontSize: 'clamp(0.6rem, 0.7vw, 0.6875rem)' }}>
                {panel.subLabel}
              </p>
              <p className="relative mt-2 leading-snug text-ink-secondary" style={{ fontSize: 'clamp(0.75rem, 0.8vw, 0.8125rem)' }}>
                {panel.description}
              </p>
            </button>
          )
        })}
      </div>

      {/* ── Drop Zone ── */}
      <div
        id="drop-zone"
        className={`relative overflow-hidden transition-all duration-200 cursor-investigator corner-bracket ${dragging ? 'scale-[1.01]' : ''}`}
        style={{
          border: `1px solid ${dragging || file ? 'var(--accent)' : 'var(--border-subtle)'}`,
          background: dragging ? 'var(--accent-soft)' : file ? 'var(--surface-2)' : 'var(--surface-1)',
          padding: 'clamp(1.5rem, 3vw, 2.5rem)',
          boxShadow: dragging ? 'var(--accent-glow)' : 'var(--shadow-sm)',
        }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files?.[0]) }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Choose a file to analyse"
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={allExtensions.join(',')}
          onChange={(e) => choose(e.target.files?.[0])}
        />

        {file ? (
          <div className="flex flex-col items-center">
            {preview ? (
              <img
                src={preview}
                alt=""
                className="mb-5 max-h-52 rounded-xl object-contain"
                style={{ boxShadow: 'var(--shadow-lg)' }}
              />
            ) : (
              <div
                className="mb-5 grid h-16 w-16 place-items-center rounded-2xl"
                style={{
                  background: activePanelDef ? `var(${activePanelDef.accentVar})` : 'var(--accent)',
                  color: '#fff',
                  boxShadow: activePanelDef ? `0 4px 20px ${activePanelDef.glowColor}` : 'var(--accent-glow)',
                }}
              >
                {activePanelDef?.id === 'audio'
                  ? <WaveformBars />
                  : activePanelDef?.id === 'video'
                  ? <VideoIcon size={28} />
                  : <ImageIcon size={28} />}
              </div>
            )}
            <p className="max-w-sm truncate font-bold text-ink-primary" style={{ fontSize: 'clamp(0.9rem, 1.1vw, 1.0625rem)' }}>
              {file.name}
            </p>
            <div className="mt-1.5 flex items-center gap-3">
              <span className="tnum text-[0.8125rem] text-ink-muted">{formatBytes(file.size)}</span>
              {activePanelDef && (
                <span
                  className="badge text-white"
                  style={{ background: activePanelDef.chipColor, fontSize: '0.625rem' }}
                >
                  {activePanelDef.label}
                </span>
              )}
            </div>
            <p className="mt-3 text-[0.75rem] text-ink-muted">Click or drop another file to replace</p>
          </div>
        ) : (
          <div className="flex flex-col items-center py-4">
            <div
              className="grid h-14 w-14 place-items-center rounded-2xl mb-4 transition-transform duration-200"
              style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}
            >
              <UploadIcon size={26} />
            </div>
            <p className="font-bold text-ink-primary" style={{ fontSize: 'clamp(1rem, 1.2vw, 1.125rem)', letterSpacing: '-0.02em' }}>
              {activePanel
                ? `Drop ${MEDIA_PANELS.find(p=>p.id===activePanel)?.label} file here`
                : 'Drop a file here, or click to browse'}
            </p>
            <p className="mt-1.5 text-ink-muted" style={{ fontSize: 'clamp(0.8125rem, 0.9vw, 0.9375rem)' }}>
              Images, Audio & Video
              {limits ? ` · up to ${limits.max_upload_mb} MB` : ''}
            </p>
          </div>
        )}
      </div>

      {/* ── Error ── */}
      {error && <Notice tone="critical" title="File not accepted">{error}</Notice>}

      {/* ── Upload progress ── */}
      {phase === 'uploading' && (
        <div
          className="card"
          style={{ padding: 'clamp(1rem, 2vw, 1.5rem)', boxShadow: 'var(--shadow-md)' }}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <Spinner size={16} />
              <span className="font-semibold text-ink-primary font-mono" style={{ fontSize: 'clamp(0.875rem, 1vw, 1rem)' }}>
                {progress < 100 ? 'Streaming to object storage...' : 'Queuing Celery Task...'}
              </span>
            </div>
            <span className="tnum font-bold text-ink-secondary" style={{ fontSize: 'clamp(0.875rem, 1vw, 1rem)' }}>
              {progress}%
            </span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full"
            style={{ background: 'var(--surface-3)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${progress}%`,
                background: activePanelDef
                  ? `var(${activePanelDef.accentVar})`
                  : 'var(--grad-accent)',
                boxShadow: activePanelDef ? `0 0 8px var(${activePanelDef.accentVar})` : 'none',
              }}
            />
          </div>
        </div>
      )}

      {/* ── Submit button ── */}
      <button
        id="btn-start-analysis"
        className={file ? 'btn-glow w-full !py-4 text-base' : 'btn-primary w-full !py-4 text-base'}
        onClick={submit}
        disabled={!file || phase !== 'idle'}
        style={file ? { fontSize: 'clamp(0.9375rem, 1vw, 1.0625rem)', borderRadius: 'var(--radius-md)' } : { borderRadius: 'var(--radius-md)' }}
      >
        {phase === 'idle'
          ? <><span>Execute Forensic Pipeline</span> <ArrowRight size={18} /></>
          : <><Spinner size={16} /> Allocating Workers...</>}
      </button>

      {/* ── Rate limit notice ── */}
      {limits && (
        <p className="text-center text-ink-muted" style={{ fontSize: 'clamp(0.75rem, 0.8vw, 0.8125rem)' }}>
          {user
            ? `Upload limit: ${limits.rate_limit_per_hour.registered} files per hour.`
            : `Guest limit: ${limits.rate_limit_per_hour.guest} files/hr — sign in for ${limits.rate_limit_per_hour.registered}.`}
        </p>
      )}
    </div>
  )
}
