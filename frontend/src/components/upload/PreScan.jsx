import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Check, Hash, Image as ImageIcon, Spinner, Video as VideoIcon, Waveform } from '../ui/Icons'

/**
 * Pre-scan: what the browser can learn about the chosen file before anything
 * is uploaded. Everything here runs locally on the real file:
 *   - SHA-256 of the bytes (the same hash the server records on upload)
 *   - images: pixel size, whether an EXIF block is present, a magnifier loupe
 *   - audio: the decoded waveform, sample rate, channels, length
 *   - video: frames grabbed at 1 per second (the pipeline's default sampling)
 */

const MAX_HASH_BYTES = 200 * 1024 * 1024

async function sha256Hex(file) {
  const buf = await file.arrayBuffer()
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

/** True if the first bytes contain an EXIF header ("Exif\0\0"). */
async function hasExifBlock(file) {
  const head = new Uint8Array(await file.slice(0, 256 * 1024).arrayBuffer())
  for (let i = 0; i < head.length - 6; i++) {
    if (head[i] === 0x45 && head[i + 1] === 0x78 && head[i + 2] === 0x69 && head[i + 3] === 0x66 && head[i + 4] === 0 && head[i + 5] === 0) return true
  }
  return false
}

async function imageInfo(file) {
  const url = URL.createObjectURL(file)
  try {
    const img = await new Promise((resolve, reject) => {
      const el = new Image()
      el.onload = () => resolve(el)
      el.onerror = reject
      el.src = url
    })
    return { width: img.naturalWidth, height: img.naturalHeight, exif: await hasExifBlock(file) }
  } finally {
    URL.revokeObjectURL(url)
  }
}

async function audioInfo(file) {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) return null
  const ctx = new Ctx()
  try {
    const buf = await ctx.decodeAudioData(await file.arrayBuffer())
    const data = buf.getChannelData(0)
    const bins = 160
    const size = Math.floor(data.length / bins) || 1
    const peaks = Array.from({ length: bins }, (_, i) => {
      let max = 0
      for (let j = i * size; j < Math.min(data.length, (i + 1) * size); j++) max = Math.max(max, Math.abs(data[j]))
      return max
    })
    const top = Math.max(...peaks) || 1
    return { peaks: peaks.map((p) => p / top), sampleRate: buf.sampleRate, channels: buf.numberOfChannels, duration: buf.duration }
  } finally {
    ctx.close?.()
  }
}

async function videoFrames(file, count = 8) {
  const url = URL.createObjectURL(file)
  const video = document.createElement('video')
  video.muted = true
  video.preload = 'auto'
  video.src = url
  try {
    await new Promise((resolve, reject) => { video.onloadeddata = resolve; video.onerror = reject })
    const { duration, videoWidth: w, videoHeight: h } = video
    const canvas = document.createElement('canvas')
    canvas.width = 192
    canvas.height = Math.round((192 * h) / (w || 1)) || 108
    const ctx = canvas.getContext('2d')
    const frames = []
    for (let t = 0; t < Math.min(duration, count); t += 1) {
      video.currentTime = Math.min(t + 0.01, Math.max(0, duration - 0.05))
      await new Promise((resolve) => { video.onseeked = resolve })
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      frames.push({ t, src: canvas.toDataURL('image/jpeg', 0.7) })
    }
    return { frames, width: w, height: h, duration }
  } finally {
    URL.revokeObjectURL(url)
  }
}

function withTimeout(promise, ms) {
  return Promise.race([promise, new Promise((resolve) => setTimeout(() => resolve(null), ms))])
}

// ── pieces ──────────────────────────────────────────────────────────────────

function Loupe({ src }) {
  const [pos, setPos] = useState(null)
  return (
    <div className="relative overflow-hidden rounded-lg border-2 border-[#191919] bg-[#191919]"
         onPointerMove={(e) => {
           const r = e.currentTarget.getBoundingClientRect()
           setPos({ x: e.clientX - r.left, y: e.clientY - r.top, w: r.width, h: r.height })
         }}
         onPointerLeave={() => setPos(null)}>
      <img src={src} alt="Preview of the chosen image" className="mx-auto max-h-72 w-full object-contain" />
      {pos && (
        <span className="pointer-events-none absolute h-32 w-32 rounded-full border-[3px] border-[var(--acid)]"
              style={{
                left: pos.x - 64, top: pos.y - 64,
                backgroundImage: `url(${src})`, backgroundRepeat: 'no-repeat',
                backgroundSize: `${pos.w * 3}px ${pos.h * 3}px`,
                backgroundPosition: `${-pos.x * 3 + 64}px ${-pos.y * 3 + 64}px`,
                boxShadow: '0 0 0 3px #191919, 6px 6px 0 #000',
              }} />
      )}
      <span className="mono pointer-events-none absolute bottom-2 left-2 rounded-sm bg-[#191919] px-1.5 py-0.5 text-[0.625rem] font-bold text-[var(--acid)]">
        hover to inspect · 3×
      </span>
    </div>
  )
}

function Row({ label, value, ok }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-dashed py-2.5" style={{ borderColor: 'var(--border-strong)' }}>
      <span className="mono text-[0.75rem] font-bold uppercase text-ink-muted">{label}</span>
      <span className="flex items-center gap-2 text-right text-[0.9375rem] font-semibold text-ink-primary">
        {ok !== undefined && <span className="h-2.5 w-2.5 rounded-full" style={{ background: ok ? 'var(--acid)' : '#ffb020' }} />}
        {value}
      </span>
    </div>
  )
}

// ── main ────────────────────────────────────────────────────────────────────

export default function PreScan({ file, kind, preview }) {
  const [hash, setHash] = useState(null)
  const [info, setInfo] = useState(undefined)
  const shown = useTypewriter(hash)

  useEffect(() => {
    let live = true
    setHash(null)
    setInfo(undefined)
    if (file.size <= MAX_HASH_BYTES && crypto?.subtle) {
      sha256Hex(file).then((h) => live && setHash(h)).catch(() => live && setHash('unavailable'))
    } else {
      setHash('unavailable')
    }
    const job = kind === 'image' ? imageInfo(file) : kind === 'audio' ? audioInfo(file) : kind === 'video' ? videoFrames(file) : Promise.resolve(null)
    withTimeout(job.catch(() => null), 15000).then((v) => live && setInfo(v))
    return () => { live = false }
  }, [file, kind])

  const Icon = kind === 'audio' ? Waveform : kind === 'video' ? VideoIcon : ImageIcon

  return (
    <motion.section initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ type: 'spring', stiffness: 200, damping: 22 }}
                    className="mt-10 overflow-hidden rounded-2xl border-2 border-[#191919]" style={{ boxShadow: '10px 10px 0 var(--teal)' }}>
      <header className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-[#191919] px-5 py-3 text-[#191919]" style={{ background: 'var(--teal)' }}>
        <span className="wide flex items-center gap-2 text-lg font-black uppercase"><Icon size={18} /> Pre-scan</span>
        <span className="mono text-[0.6875rem] font-bold uppercase">runs in your browser · nothing uploaded yet</span>
      </header>

      <div className="grid gap-6 p-5 sm:p-7 lg:grid-cols-[1.3fr_1fr]" style={{ background: 'var(--surface-1)' }}>
        {/* visual */}
        <div className="min-w-0">
          {kind === 'image' && preview && <Loupe src={preview} />}

          {kind === 'audio' && (
            info?.peaks ? (
              <div className="flex h-44 items-center gap-[2px] rounded-lg border-2 border-[#191919] bg-[#191919] px-3">
                {info.peaks.map((p, i) => (
                  <motion.span key={i} className="flex-1 rounded-full" style={{ background: i % 25 === 0 ? 'var(--acid)' : 'var(--teal)' }}
                               initial={{ height: 2 }} animate={{ height: `${Math.max(3, p * 92)}%` }} transition={{ delay: i * 0.004 }} />
                ))}
              </div>
            ) : <Pending failed={info === null} label={info === null ? 'Your browser could not decode this audio; the server will.' : 'Decoding the waveform…'} />
          )}

          {kind === 'video' && (
            info?.frames?.length ? (
              <div>
                <div className="flex gap-2 overflow-x-auto rounded-lg border-2 border-[#191919] bg-[#191919] p-2">
                  {info.frames.map((f, i) => (
                    <motion.figure key={f.t} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                                   className="relative w-36 shrink-0">
                      <img src={f.src} alt={`Frame at ${f.t} seconds`} className="w-full rounded-sm border border-[#444449]" />
                      <figcaption className="mono absolute bottom-1 left-1 rounded-sm bg-[#191919] px-1 text-[0.5625rem] font-bold text-[var(--acid)]">{f.t}s</figcaption>
                    </motion.figure>
                  ))}
                </div>
                <p className="mono mt-2 text-[0.6875rem] text-ink-muted">1 frame per second, as the video pipeline samples by default (first {info.frames.length} shown).</p>
              </div>
            ) : <Pending failed={info === null} label={info === null ? 'Your browser could not read frames from this video; the server will.' : 'Grabbing frames…'} />
          )}
        </div>

        {/* facts */}
        <div className="min-w-0">
          <Row label="File" value={<span className="block max-w-[14rem] truncate" title={file.name}>{file.name}</span>} />
          {kind === 'image' && info && (
            <>
              <Row label="Pixels" value={`${info.width} × ${info.height}`} ok={info.width >= 128 && info.height >= 128} />
              <Row label="EXIF block" value={info.exif ? 'found' : 'not found'} ok={info.exif} />
            </>
          )}
          {kind === 'audio' && info && (
            <>
              <Row label="Sample rate" value={`${(info.sampleRate / 1000).toFixed(1)} kHz`} />
              <Row label="Channels" value={info.channels === 1 ? 'mono' : `${info.channels}`} />
              <Row label="Length" value={`${info.duration.toFixed(1)} s`} />
            </>
          )}
          {kind === 'video' && info && (
            <>
              <Row label="Resolution" value={`${info.width} × ${info.height}`} />
              <Row label="Length" value={`${info.duration.toFixed(1)} s`} />
            </>
          )}

          <div className="mt-4 rounded-lg border-2 border-[#191919] p-3" style={{ background: '#191919' }}>
            <span className="mono flex items-center gap-2 text-[0.6875rem] font-bold uppercase text-[#a7a7ab]">
              <Hash size={12} /> SHA-256 {hash && hash !== 'unavailable' && <Check size={12} className="text-[var(--acid)]" />}
            </span>
            <p className="mono mt-1.5 break-all text-[0.75rem] leading-relaxed text-[var(--acid)]" aria-live="polite">
              {hash === null ? <span className="inline-flex items-center gap-2 text-[#8a8a92]"><Spinner size={12} /> hashing…</span>
                : hash === 'unavailable' ? <span className="text-[#8a8a92]">computed on the server after upload</span>
                : shown}
            </p>
          </div>
          <p className="mt-3 text-[0.8125rem] leading-relaxed text-ink-secondary">
            {kind === 'image'
              ? 'The server records this same fingerprint. Without camera metadata an image is called authentic only at a very low AI score, so a missing EXIF block makes “inconclusive” more likely.'
              : 'The server records this same fingerprint, so the PDF report can be matched to this exact file.'}
          </p>
        </div>
      </div>
    </motion.section>
  )
}

function Pending({ label, failed = false }) {
  return (
    <div className="grid h-44 place-items-center rounded-lg border-2 border-dashed text-[0.875rem] text-ink-muted" style={{ borderColor: 'var(--border-strong)' }}>
      <span className="flex items-center gap-2 px-4 text-center">{!failed && <Spinner size={14} />} {label}</span>
    </div>
  )
}

/** Types a string out character by character. */
function useTypewriter(text) {
  const [n, setN] = useState(0)
  const timer = useRef(0)
  useEffect(() => {
    setN(0)
    if (!text || text === 'unavailable') return undefined
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setN(text.length); return undefined }
    timer.current = window.setInterval(() => setN((v) => {
      if (v >= text.length) { window.clearInterval(timer.current); return v }
      return v + 2
    }), 16)
    return () => window.clearInterval(timer.current)
  }, [text])
  return text ? text.slice(0, n) : ''
}
