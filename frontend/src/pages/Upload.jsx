import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../lib/api'
import { formatBytes } from '../lib/format'
import { useAuth } from '../lib/useAuth'
import { Notice } from '../components/ui'
import PreScan from '../components/upload/PreScan'
import {
  AlertTriangle, ArrowRight, Check, Hash, Image as ImageIcon, Lock, Spinner,
  Upload as UploadIcon, Video as VideoIcon, Waveform, X,
} from '../components/ui/Icons'

// ── Media types ──────────────────────────────────────────────────────────────
// Fallback extension lists for when /upload/limits is unreachable; the API's
// own lists win when they arrive.
const MEDIA = [
  { id: 'image', label: 'Image', icon: ImageIcon, color: 'var(--acid)',
    formats: 'JPG · PNG · WEBP · HEIC · AVIF · TIFF',
    extensions: ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif', '.heic', '.heif', '.tiff', '.tif', '.gif', '.ico', '.jfif'] },
  { id: 'audio', label: 'Audio', icon: Waveform, color: 'var(--teal)',
    formats: 'WAV · MP3 · FLAC · OGG · M4A · OPUS',
    extensions: ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus', '.aiff', '.alac'] },
  { id: 'video', label: 'Video', icon: VideoIcon, color: 'var(--mint)',
    formats: 'MP4 · MOV · AVI · MKV · WEBM',
    extensions: ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.ts', '.3gp'] },
]

// Sourced from KNOWN_ISSUES.md (#14, #16, #17) and the model card.
const NEXT = [
  ['1', 'Fingerprint', 'The file is hashed with SHA-256 as it is saved, so the report can be tied to these exact bytes.'],
  ['2', 'Queue', 'A worker picks up the job and you watch its progress live. Images take seconds; video takes longer.'],
  ['3', 'Score', 'The detectors for your media type score it. Borderline scores become \u201cinconclusive\u201d.'],
  ['4', 'Read & download', 'See the verdict and the evidence behind it, then download the PDF report or delete the scan.'],
]

const TIPS = [
  [ImageIcon, 'Upload the original', 'Screenshots and re-shares strip camera metadata and provenance, which makes a confident answer harder.'],
  [Waveform, 'Prefer lossless audio', 'WAV or FLAC is best. Heavy compression and phone-call audio can mislead the audio models.'],
  [VideoIcon, 'Keep the face in view', 'The video face-swap check needs visible faces. Without one, it does not apply.'],
  [AlertTriangle, 'Read inconclusive as honest', 'The newest image generators are often returned as inconclusive rather than flagged.'],
]

const suffixOf = (name) => name.slice(name.lastIndexOf('.')).toLowerCase()

/** Reads an audio or video file's duration in the browser (null if it can't). */
function readDuration(file, kind) {
  return new Promise((resolve) => {
    const el = document.createElement(kind === 'video' ? 'video' : 'audio')
    const url = URL.createObjectURL(file)
    const done = (v) => { URL.revokeObjectURL(url); resolve(v) }
    el.preload = 'metadata'
    el.onloadedmetadata = () => done(Number.isFinite(el.duration) ? el.duration : null)
    el.onerror = () => done(null)
    window.setTimeout(() => done(null), 4000)
    el.src = url
  })
}

function fmtSeconds(s) {
  if (s == null) return '?'
  const m = Math.floor(s / 60)
  const r = Math.round(s % 60)
  return m ? `${m} min${r ? ` ${r} s` : ""}` : `${Math.round(s)} s`
}

// ── Pieces ───────────────────────────────────────────────────────────────────

function Steps({ current }) {
  const steps = ['Choose', 'Check', 'Upload']
  return (
    <ol className="flex items-center gap-2" aria-label="Progress">
      {steps.map((s, i) => {
        const state = i < current ? 'done' : i === current ? 'now' : 'next'
        return (
          <li key={s} className="flex items-center gap-2">
            <span className="mono flex items-center gap-2 rounded-md border-2 px-2.5 py-1 text-[0.75rem] font-bold uppercase transition-all duration-300"
                  style={{
                    borderColor: state === 'next' ? 'var(--border-strong)' : '#191919',
                    background: state === 'now' ? 'var(--acid)' : state === 'done' ? 'var(--mint-soft)' : 'transparent',
                    color: state === 'next' ? 'var(--text-muted)' : '#191919',
                    boxShadow: state === 'now' ? '3px 3px 0 var(--pop)' : 'none',
                  }}
                  aria-current={state === 'now' ? 'step' : undefined}>
              {state === 'done' ? <Check size={13} /> : <span>{i + 1}</span>}
              {s}
            </span>
            {i < steps.length - 1 && <span className="h-0.5 w-4 sm:w-8" style={{ background: i < current ? 'var(--acid)' : 'var(--border-strong)' }} />}
          </li>
        )
      })}
    </ol>
  )
}

/** Target with the three media icons orbiting it: the empty state of the zone. */
function OrbitTarget({ dragging }) {
  return (
    <div className="relative mx-auto h-40 w-40 sm:h-48 sm:w-48" aria-hidden="true">
      <div className="spin-slow absolute inset-0 rounded-full border-2 border-dashed" style={{ borderColor: dragging ? '#191919' : 'var(--border-strong)' }}>
        {MEDIA.map((m, i) => (
          <span key={m.id} className="absolute grid h-11 w-11 place-items-center rounded-md border-2 border-[#191919]"
                style={{
                  background: m.color, color: '#191919',
                  left: `${50 + 50 * Math.cos((i * 2 * Math.PI) / 3 - Math.PI / 2)}%`,
                  top: `${50 + 50 * Math.sin((i * 2 * Math.PI) / 3 - Math.PI / 2)}%`,
                  transform: 'translate(-50%, -50%)',
                }}>
            <span className="spin-slow-reverse grid place-items-center"><m.icon size={20} /></span>
          </span>
        ))}
      </div>
      <motion.span className="absolute inset-[26%] grid place-items-center rounded-full border-2 border-[#191919]"
                   style={{ background: dragging ? '#191919' : 'var(--acid)', color: dragging ? 'var(--acid)' : '#191919' }}
                   animate={dragging ? { scale: [1, 1.12, 1] } : { scale: 1 }}
                   transition={dragging ? { repeat: Infinity, duration: 0.8 } : {}}>
        <UploadIcon size={30} />
      </motion.span>
    </div>
  )
}

/** Visual stand-in for files that have no image preview. */
function MediaPlaceholder({ kind }) {
  if (kind === 'audio') {
    return (
      <div className="flex h-36 w-full items-center gap-[3px] rounded-lg border-2 border-[#191919] bg-[#191919] px-4">
        {Array.from({ length: 40 }, (_, i) => (
          <span key={i} className="eq-bar flex-1" style={{ height: `${25 + 70 * Math.abs(Math.sin(i * 0.5) * Math.cos(i * 0.17))}%`, background: 'var(--teal)', animationDelay: `${(i % 10) * 0.07}s` }} />
        ))}
      </div>
    )
  }
  if (kind === 'video') {
    return (
      <div className="flex h-36 w-full gap-1.5 rounded-lg border-2 border-[#191919] bg-[#191919] p-2">
        {Array.from({ length: 6 }, (_, i) => (
          <motion.span key={i} className="flex-1 rounded-sm" style={{ background: '#28282b' }}
                       animate={{ background: ['#28282b', '#57c690', '#28282b'] }}
                       transition={{ repeat: Infinity, duration: 2.4, delay: i * 0.4 }} />
        ))}
      </div>
    )
  }
  return null
}

function CheckRow({ state, children }) {
  const style = {
    ok: { bg: 'var(--acid)', icon: <Check size={13} /> },
    bad: { bg: '#ff4d3d', icon: <X size={13} /> },
    wait: { bg: 'var(--surface-3)', icon: <Spinner size={12} /> },
    info: { bg: 'var(--mint-soft)', icon: <Hash size={12} /> },
  }[state]
  return (
    <motion.li initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} className="flex items-start gap-3">
      <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md border-2 border-[#191919] text-[#191919]" style={{ background: style.bg }}>
        {style.icon}
      </span>
      <span className="text-[0.9375rem] font-medium text-ink-primary">{children}</span>
    </motion.li>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const [limits, setLimits] = useState(null)
  const [file, setFile] = useState(null)
  const [kind, setKind] = useState(null)
  const [preview, setPreview] = useState(null)
  const [duration, setDuration] = useState(undefined) // undefined = not read yet
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState('idle')
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const dragDepth = useRef(0)
  const navigate = useNavigate()
  const { user } = useAuth()

  useEffect(() => {
    api.limits().then(setLimits).catch(() => setLimits(null))
  }, [])

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  // The whole page is a drop target, and Ctrl/Cmd+V pastes a copied image or
  // file. Listeners live on window and call the latest choose() via a ref.
  // Dragging over child elements fires leave/enter pairs; the depth counter
  // keeps the highlight from flickering.
  const chooseRef = useRef(null)
  const phaseRef = useRef('idle')
  useEffect(() => {
    const hasFiles = (e) => Array.from(e.dataTransfer?.types || []).includes('Files')
    const onEnter = (e) => {
      if (!hasFiles(e) || phaseRef.current !== 'idle') return
      e.preventDefault(); dragDepth.current += 1; setDragging(true)
    }
    const onOver = (e) => { if (hasFiles(e)) e.preventDefault() }
    const onLeave = (e) => {
      if (!hasFiles(e)) return
      dragDepth.current -= 1
      if (dragDepth.current <= 0) { dragDepth.current = 0; setDragging(false) }
    }
    const onDrop = (e) => {
      if (!hasFiles(e)) return
      e.preventDefault(); dragDepth.current = 0; setDragging(false)
      if (phaseRef.current === 'idle') chooseRef.current?.(e.dataTransfer.files?.[0])
    }
    const onPaste = (e) => {
      const pasted = e.clipboardData?.files?.[0]
      if (pasted && phaseRef.current === 'idle') { e.preventDefault(); chooseRef.current?.(pasted) }
    }
    window.addEventListener('dragenter', onEnter)
    window.addEventListener('dragover', onOver)
    window.addEventListener('dragleave', onLeave)
    window.addEventListener('drop', onDrop)
    window.addEventListener('paste', onPaste)
    return () => {
      window.removeEventListener('dragenter', onEnter)
      window.removeEventListener('dragover', onOver)
      window.removeEventListener('dragleave', onLeave)
      window.removeEventListener('drop', onDrop)
      window.removeEventListener('paste', onPaste)
    }
  }, [])

  const enabled = (id) => !limits || (limits.enabled_media_types || []).includes(id)
  const extsFor = (m) => limits?.allowed_extensions?.[m.id] || (enabled(m.id) ? m.extensions : [])
  const allExtensions = MEDIA.flatMap(extsFor)
  const kindOf = (name) => MEDIA.find((m) => extsFor(m).includes(suffixOf(name)))?.id || null
  const maxSeconds = (k) => limits?.max_duration_seconds?.[k] ?? null

  function validate(candidate) {
    const suffix = suffixOf(candidate.name)
    if (!allExtensions.includes(suffix)) {
      const disabled = MEDIA.find((m) => m.extensions.includes(suffix) && !enabled(m.id))
      return disabled
        ? `${disabled.label} analysis is not enabled on this server.`
        : `Unsupported file type "${suffix || 'unknown'}".`
    }
    if (limits && candidate.size > limits.max_upload_mb * 1024 * 1024)
      return `File is ${formatBytes(candidate.size)}; limit is ${limits.max_upload_mb} MB.`
    return null
  }

  function choose(candidate) {
    if (!candidate) return
    const problem = validate(candidate)
    setError(problem)
    if (problem) { setFile(null); setPreview(null); setKind(null); return }
    const k = kindOf(candidate.name)
    setFile(candidate)
    setKind(k)
    setPreview(candidate.type.startsWith('image/') ? URL.createObjectURL(candidate) : null)
    setDuration(undefined)
    if (k === 'audio' || k === 'video') readDuration(candidate, k).then(setDuration)
    else setDuration(null)
  }

  function clear(e) {
    e.stopPropagation()
    setFile(null); setPreview(null); setKind(null); setError(null)
    if (inputRef.current) inputRef.current.value = ''
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

  chooseRef.current = choose
  phaseRef.current = phase

  const tooLong = duration != null && maxSeconds(kind) != null && duration > maxSeconds(kind)
  const step = phase === 'uploading' ? 2 : file ? 1 : 0
  const media = MEDIA.find((m) => m.id === kind)

  return (
    <div className="mx-auto max-w-6xl">
      {/* full-screen drop target while a file is dragged over the window */}
      <AnimatePresence>
        {dragging && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      className="pointer-events-none fixed inset-0 z-[75] grid place-items-center p-6"
                      style={{ background: 'rgba(35,248,113,0.92)', color: '#191919' }} aria-hidden="true">
            <div className="absolute inset-6 rounded-3xl border-4 border-dashed border-[#191919]" />
            <motion.div initial={{ scale: 0.8, rotate: -4 }} animate={{ scale: 1, rotate: -2 }} transition={{ type: 'spring', stiffness: 260, damping: 14 }}
                        className="text-center">
              <UploadIcon size={64} className="mx-auto" />
              <p className="wide mt-4 font-black uppercase" style={{ fontSize: 'clamp(3rem, 9vw, 8rem)', lineHeight: 0.85, letterSpacing: '-0.06em' }}>
                Drop it<br /><span className="serif-i normal-case">anywhere.</span>
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Header ── */}
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <span className="eyebrow">New scan</span>
          <h1 className="wide mt-4 font-black uppercase text-ink-primary"
              style={{ fontSize: 'clamp(2.5rem, 6vw, 5.25rem)', lineHeight: 0.88, letterSpacing: '-0.055em' }}>
            Analyse a <span className="serif-i normal-case text-gradient">file.</span>
          </h1>
          <p className="mt-4 max-w-xl text-[1.0625rem] leading-relaxed text-ink-secondary">
            Drop an image, voice clip or video. We record its SHA-256 fingerprint, run the detectors for
            that media type, and show you the verdict with the evidence behind it.
          </p>
        </div>
        <Steps current={step} />
      </div>

      <div className="mt-10 grid gap-8 lg:grid-cols-[1.45fr_1fr]">
        {/* ── Intake tray (drop zone) ── */}
        <div
          id="drop-zone"
          onClick={() => phase === 'idle' && inputRef.current?.click()}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && phase === 'idle' && inputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Choose a file to analyse"
          className={`intake relative flex min-h-[26rem] cursor-pointer flex-col justify-center overflow-hidden rounded-2xl p-6 transition-all duration-300 sm:p-10 ${dragging ? 'is-dragging' : ''}`}
          style={{
            backgroundColor: dragging ? 'var(--acid)' : 'var(--surface-1)',
            color: dragging ? '#191919' : undefined,
            boxShadow: dragging ? '12px 12px 0 var(--pop)' : file ? '10px 10px 0 var(--acid)' : '8px 8px 0 #000',
            transform: dragging ? 'translate(-4px,-4px) rotate(-0.5deg)' : 'none',
          }}
        >
          <input ref={inputRef} type="file" className="hidden" accept={allExtensions.join(',')}
                 onChange={(e) => choose(e.target.files?.[0])} />

          {/* grid backdrop + corner marks */}
          <div className="pointer-events-none absolute inset-0 opacity-60"
               style={{ backgroundImage: 'linear-gradient(var(--grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--grid-line) 1px, transparent 1px)', backgroundSize: '28px 28px' }} aria-hidden="true" />
          {['left-4 top-4 border-l-4 border-t-4', 'right-4 top-4 border-r-4 border-t-4', 'bottom-4 left-4 border-b-4 border-l-4', 'bottom-4 right-4 border-b-4 border-r-4'].map((c) => (
            <span key={c} className={`pointer-events-none absolute h-7 w-7 ${c}`} style={{ borderColor: dragging ? '#191919' : 'var(--acid)' }} aria-hidden="true" />
          ))}
          {phase === 'uploading' && <div className="scanline pointer-events-none absolute inset-0" aria-hidden="true" />}

          <AnimatePresence mode="wait">
            {!file ? (
              <motion.div key="empty" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }}
                          className="relative text-center">
                <OrbitTarget dragging={dragging} />
                <p className="wide mt-8 font-black uppercase" style={{ fontSize: 'clamp(1.5rem, 3vw, 2.5rem)', lineHeight: 0.95, letterSpacing: '-0.04em' }}>
                  {dragging ? 'Release to scan' : 'Drop a file here'}
                </p>
                {!dragging && (
                  <>
                    <p className="mt-3 text-ink-secondary">or</p>
                    <span className="btn-primary btn-lg mt-3 uppercase" style={{ fontStretch: '115%', fontWeight: 800 }}>
                      <UploadIcon size={18} /> Choose a file
                    </span>
                    <p className="mono mt-5 text-[0.75rem] text-ink-muted">
                      One file at a time{limits ? ` · up to ${limits.max_upload_mb} MB` : ''}
                    </p>
                    <p className="mono mt-2 hidden text-[0.75rem] text-ink-muted sm:block">
                      Tip: drop anywhere on the page, or paste with{' '}
                      <kbd className="rounded-sm border-2 border-[var(--border-strong)] px-1 font-bold text-ink-primary">Ctrl</kbd>+<kbd className="rounded-sm border-2 border-[var(--border-strong)] px-1 font-bold text-ink-primary">V</kbd>
                    </p>
                  </>
                )}
              </motion.div>
            ) : (
              <motion.div key="file" initial={{ opacity: 0, y: 20, rotate: -2 }} animate={{ opacity: 1, y: 0, rotate: 0 }} exit={{ opacity: 0, y: -20 }}
                          transition={{ type: 'spring', stiffness: 260, damping: 20 }} className="relative">
                {/* evidence tag */}
                <div className="relative mx-auto max-w-md rounded-xl border-2 border-[#191919] p-4 text-[#191919]" style={{ background: '#ececed', boxShadow: '6px 6px 0 #191919' }}>
                  <span className="absolute -top-3 left-6 h-6 w-20 -rotate-3 opacity-90" style={{ background: media?.color || 'var(--acid)' }} aria-hidden="true" />
                  <div className="flex items-center justify-between">
                    <span className="mono text-[0.6875rem] font-bold uppercase">Evidence tag</span>
                    <button onClick={clear} disabled={phase !== 'idle'} aria-label="Remove file"
                            className="grid h-7 w-7 place-items-center rounded-md border-2 border-[#191919] transition-colors hover:bg-[#ff4d3d] disabled:opacity-40">
                      <X size={14} />
                    </button>
                  </div>
                  <div className="mt-3">
                    {preview
                      ? <img src={preview} alt="" className="mx-auto max-h-56 rounded-lg border-2 border-[#191919] object-contain" />
                      : <MediaPlaceholder kind={kind} />}
                  </div>
                  <p className="mt-4 truncate text-[1.0625rem] font-bold" title={file.name}>{file.name}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {media && (
                      <span className="mono inline-flex items-center gap-1.5 rounded-sm border-2 border-[#191919] px-2 py-0.5 text-[0.6875rem] font-bold uppercase" style={{ background: media.color }}>
                        <media.icon size={12} /> {media.label}
                      </span>
                    )}
                    <span className="mono text-[0.75rem] font-bold">{formatBytes(file.size)}</span>
                    {duration != null && <span className="mono text-[0.75rem] font-bold">· {fmtSeconds(duration)}</span>}
                  </div>
                </div>
                <p className="mono mt-5 text-center text-[0.75rem] text-ink-muted">Click or drop another file to replace it</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Side panel: checks, action, limits ── */}
        <div className="flex flex-col gap-6">
          <div className="rounded-2xl border-2 p-6" style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-1)' }}>
            <h2 className="wide text-lg font-black uppercase tracking-tight">Pre-flight checks</h2>
            {file ? (
              <ul className="mt-4 space-y-3">
                <CheckRow state="ok">{media?.label || 'File'} type is supported</CheckRow>
                <CheckRow state="ok">{formatBytes(file.size)}{limits ? ` is under the ${limits.max_upload_mb} MB limit` : ''}</CheckRow>
                {(kind === 'audio' || kind === 'video') && (
                  duration === undefined
                    ? <CheckRow state="wait">Reading the length…</CheckRow>
                    : tooLong
                      ? <CheckRow state="bad">{fmtSeconds(duration)} is longer than the {fmtSeconds(maxSeconds(kind))} limit for {kind}</CheckRow>
                      : <CheckRow state="ok">Length {fmtSeconds(duration)}{maxSeconds(kind) ? `, limit ${fmtSeconds(maxSeconds(kind))}` : ''}</CheckRow>
                )}
                <CheckRow state="info">A SHA-256 fingerprint will be recorded on upload</CheckRow>
              </ul>
            ) : (
              <p className="mt-3 text-[0.9375rem] text-ink-secondary">Choose a file and we check it here before anything is sent.</p>
            )}
          </div>

          {error && <Notice tone="critical" title="File not accepted">{error}</Notice>}
          {tooLong && !error && (
            <Notice tone="warn" title="This file will be refused">
              Trim it to under {fmtSeconds(maxSeconds(kind))} and try again.
            </Notice>
          )}

          {/* upload progress */}
          {phase === 'uploading' && (
            <div className="rounded-2xl border-2 border-[#191919] p-5" style={{ background: 'var(--surface-1)', boxShadow: '6px 6px 0 var(--acid)' }}>
              <div className="flex items-end justify-between">
                <span className="mono text-[0.75rem] font-bold uppercase text-ink-secondary">
                  {progress < 100 ? 'Uploading' : 'Queued for analysis'}
                </span>
                <span className="wide tnum text-4xl font-black leading-none">{progress}%</span>
              </div>
              <div className="mt-3 h-5 overflow-hidden rounded-sm border-2 border-[#191919]" style={{ background: 'var(--surface-3)' }}>
                <div className="h-full transition-all duration-300"
                     style={{ width: `${progress}%`, background: 'repeating-linear-gradient(45deg, var(--acid) 0 12px, var(--acid-2) 12px 24px)' }} />
              </div>
            </div>
          )}

          <button
            id="btn-start-analysis"
            className="btn-glow btn-lg w-full !py-5 text-[1.0625rem]"
            onClick={submit}
            disabled={!file || phase !== 'idle' || tooLong}
          >
            {phase === 'idle'
              ? <>Start analysis <ArrowRight size={20} /></>
              : <><Spinner size={18} /> Uploading…</>}
          </button>

          {/* media type chips */}
          <div className="grid grid-cols-3 gap-2">
            {MEDIA.map((m) => {
              const on = enabled(m.id)
              const active = kind === m.id
              return (
                <button key={m.id} id={`panel-${m.id}`} type="button" disabled={!on || phase !== 'idle'}
                        onClick={() => inputRef.current?.click()}
                        title={on ? m.formats : `${m.label} is not enabled on this server`}
                        className="group rounded-xl border-2 p-3 text-left transition-all duration-200 enabled:hover:-translate-x-0.5 enabled:hover:-translate-y-0.5 disabled:cursor-not-allowed"
                        style={{
                          borderColor: active ? '#191919' : 'var(--border-strong)',
                          background: active ? m.color : 'var(--surface-1)',
                          color: active ? '#191919' : undefined,
                          boxShadow: active ? '4px 4px 0 var(--pop)' : 'none',
                          opacity: on ? 1 : 0.45,
                        }}>
                  <m.icon size={20} />
                  <span className="wide mt-2 block text-[0.9375rem] font-black uppercase leading-none">{m.label}</span>
                  <span className="mono mt-1 block text-[0.5625rem] leading-tight opacity-70">{on ? m.formats : 'Not enabled'}</span>
                  {on && maxSeconds(m.id) && <span className="mono mt-1 block text-[0.5625rem] opacity-70">max {fmtSeconds(maxSeconds(m.id))}</span>}
                </button>
              )
            })}
          </div>

          {/* limits + privacy */}
          <div className="space-y-2 rounded-xl border-2 border-dashed p-4 text-[0.8125rem] text-ink-secondary" style={{ borderColor: 'var(--border-strong)' }}>
            {limits && (
              <p className="flex items-center gap-2">
                <AlertTriangle size={14} className="shrink-0 text-accent" />
                {user
                  ? `Upload limit: ${limits.rate_limit_per_hour.registered} files per hour.`
                  : `Guest limit: ${limits.rate_limit_per_hour.guest} files per hour. Sign in for ${limits.rate_limit_per_hour.registered}.`}
              </p>
            )}
            <p className="flex items-start gap-2">
              <Lock size={14} className="mt-0.5 shrink-0 text-accent" />
              <span>
                {limits?.guest_retention_hours
                  ? `Guest uploads are deleted after ${limits.guest_retention_hours} hours. `
                  : 'Uploads are deleted automatically. '}
                Read the <Link to="/privacy" className="link">Privacy &amp; Data Retention policy</Link>.
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* ── Pre-scan: what the browser can tell before upload ── */}
      {file && <PreScan key={file.name + file.size + file.lastModified} file={file} kind={kind} preview={preview} />}

      {/* ── What happens next ── */}
      <section className="mt-20">
        <span className="eyebrow">What happens next</span>
        <ol className="mt-8 grid gap-6 md:grid-cols-4">
          {NEXT.map(([n, t, b], i) => (
            <motion.li key={t} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                       transition={{ delay: i * 0.08, type: 'spring', stiffness: 200, damping: 18 }}
                       className="relative rounded-xl border-2 border-[#191919] p-5 text-[#191919]"
                       style={{ background: i % 2 ? 'var(--mint-soft)' : '#ececed', boxShadow: '5px 5px 0 #000' }}>
              <span className="wide absolute -top-6 right-4 grid h-11 w-11 place-items-center rounded-md border-2 border-[#191919] bg-[var(--acid)] text-xl font-black">{n}</span>
              <h3 className="wide text-lg font-black uppercase">{t}</h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed">{b}</p>
            </motion.li>
          ))}
        </ol>
      </section>

      {/* ── Tips for a fair result ── */}
      <section className="mt-16">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="wide font-black uppercase" style={{ fontSize: 'clamp(1.75rem, 3.5vw, 3rem)', lineHeight: 0.92, letterSpacing: '-0.05em' }}>
            Get the <span className="serif-i normal-case text-gradient">fairest</span> result
          </h2>
          <Link to="/how-it-works#limits" className="link mono text-[0.8125rem]">All known limits →</Link>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {TIPS.map(([Icon, t, b], i) => (
            <motion.div key={t} initial={{ opacity: 0, rotate: i % 2 ? 2 : -2, y: 20 }} whileInView={{ opacity: 1, rotate: 0, y: 0 }} viewport={{ once: true }}
                        transition={{ delay: i * 0.06 }}
                        className="group rounded-xl border-2 p-5 transition-all hover:-translate-y-1 hover:border-[#191919] hover:shadow-[6px_6px_0_var(--acid)]"
                        style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-1)' }}>
              <span className="grid h-10 w-10 place-items-center rounded-md border-2 border-[#191919] bg-[var(--acid)] text-[#191919] transition-transform group-hover:rotate-12"><Icon size={18} /></span>
              <h3 className="mt-4 font-bold text-ink-primary">{t}</h3>
              <p className="mt-1.5 text-[0.875rem] leading-relaxed text-ink-secondary">{b}</p>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  )
}
