import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Notice } from '../components/ui'
import ScanField from '../components/fx/ScanField'
import Spotlight from '../components/fx/Spotlight'
import Marquee from '../components/fx/Marquee'
import Magnetic from '../components/fx/Magnetic'
import Scramble from '../components/fx/Scramble'
import HomoglyphLab from '../components/fx/HomoglyphLab'
import FingerprintLab from '../components/fx/FingerprintLab'
import Manifesto from '../components/landing/Manifesto'
import ScanFilm from '../components/landing/ScanFilm'
import {
  ArrowRight, Image as ImageIcon,
  Lock, ShieldQuestion, Trash, Video as VideoIcon, Waveform,
} from '../components/ui/Icons'

// ─── Content ────────────────────────────────────────────────────────────────
// No accuracy figures here on purpose: every number the product shows comes
// from an evaluation script and its results file (see How it works).

const MODALITIES = [
  {
    id: 'image', label: 'Images', icon: ImageIcon,
    bg: 'var(--acid)', fg: '#191919', shadow: '#ececed',
    kicker: 'JPG · PNG · WEBP',
    body: 'Scene-level AI-generation detectors and a face model score the picture. A heatmap shows where the models looked, alongside metadata and compression notes.',
    limit: 'The newest generators are often returned as inconclusive rather than flagged.',
  },
  {
    id: 'audio', label: 'Voice & audio', icon: Waveform,
    bg: 'var(--teal)', fg: '#191919', shadow: 'var(--acid)',
    kicker: 'WAV · MP3 · FLAC',
    body: 'A trained speech anti-spoofing model scores the clip in short windows, so you see which seconds drove the result on a timeline.',
    limit: 'Heavy codecs and narrowband phone audio can mislead the model.',
  },
  {
    id: 'video', label: 'Video', icon: VideoIcon,
    bg: 'var(--mint-soft)', fg: '#191919', shadow: 'var(--acid)',
    kicker: 'MP4 · MOV · WEBM',
    body: 'Frames are sampled across the clip, faces are tracked, and each track is scored. A timeline shows where suspicious frames cluster.',
    limit: 'With no face in the frame, the face-swap check does not apply.',
  },
]

const PRINCIPLES = [
  { icon: ShieldQuestion, title: 'Inconclusive is an answer.', body: 'Borderline scores are reported as inconclusive instead of being forced into real or fake.' },
  { icon: Lock, title: 'Unvalidated means unvalidated.', body: 'Heuristic checks are shown as supporting notes, clearly marked, and carry no weight in the verdict.' },
  { icon: Trash, title: 'Your files, your call.', body: 'Delete a scan and its upload, evidence files and report go with it. Guest uploads expire automatically.' },
]

const TAPE_A = ['Images', 'Voice clips', 'Video', 'SHA-256', 'Heatmaps', 'Timelines', 'Face tracks', 'PDF reports']
const TAPE_B = ['Look closer', 'Inconclusive is an answer', 'No sign-up needed', 'Delete any scan', 'Look closer', 'Check before you share']

// Draggable stickers scattered over the hero.
const STICKERS = [
  { text: '★ No sign-up', r: -8, pos: 'left-0 top-[34%]', bg: 'var(--acid)' },
  { text: 'SHA-256 ✓', r: 6, pos: 'right-0 top-[18%]', bg: 'var(--mint-soft)' },
  { text: 'Inconclusive is OK', r: -4, pos: 'right-0 bottom-[24%]', bg: 'var(--teal)' },
  { text: 'Drag me ↗', r: 10, pos: 'left-[2%] bottom-[10%]', bg: '#ececed' },
]

const ease = [0.2, 0.9, 0.3, 1]

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 40 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.7, delay, ease },
})

// ─── Pieces ─────────────────────────────────────────────────────────────────

/** Headline line whose words pop up out of a mask one after another. */
function KineticLine({ words, delay = 0, className = '' }) {
  return (
    <span className={`block ${className}`}>
      {words.map((w, i) => (
        <span key={i} className="inline-block overflow-hidden pb-[0.06em] align-bottom">
          <motion.span
            className={`inline-block ${w.className || ''}`}
            initial={{ y: '115%', rotate: 6 }}
            animate={{ y: 0, rotate: 0 }}
            transition={{ duration: 0.8, delay: delay + i * 0.09, ease }}
            {...(w.glitch ? { 'data-text': w.text } : {})}
          >
            {w.text}
          </motion.span>
          {i < words.length - 1 && ' '}
        </span>
      ))}
    </span>
  )
}

function SectionHead({ index, label, title, sub, dark = false }) {
  return (
    <motion.div {...reveal()} className="mb-12 lg:mb-16">
      <div className="flex items-center gap-4">
        <span className="sticker" style={{ '--r': '-2deg' }}>{index}</span>
        <span className="mono text-[0.75rem] font-bold uppercase tracking-wider"
              style={{ color: dark ? '#a7e1c5' : 'var(--text-muted)' }}>{label}</span>
      </div>
      <h2 className="wide mt-6 font-black uppercase"
          style={{ fontSize: 'clamp(2.25rem, 5.6vw, 5.25rem)', lineHeight: 0.92, letterSpacing: '-0.05em' }}>
        {title}
      </h2>
      {sub && (
        <p className="mt-5 text-[1.0625rem] leading-relaxed"
           style={{ maxWidth: '52ch', color: dark ? '#a7e1c5' : 'var(--text-secondary)' }}>
          {sub}
        </p>
      )}
    </motion.div>
  )
}

// Tiny looping visuals, one per media type (dark plates on the coloured cards).
function ImageVisual() {
  return (
    <div className="scanline relative h-full overflow-hidden rounded-md border-2 border-[#191919]" style={{ background: '#191919' }}>
      <div className="absolute inset-0" style={{ backgroundImage: 'linear-gradient(rgba(35,248,113,.12) 1px, transparent 1px), linear-gradient(90deg, rgba(35,248,113,.12) 1px, transparent 1px)', backgroundSize: '16px 16px' }} />
      <div className="heat-blob absolute left-[34%] top-[16%] h-[66%] w-[34%] rounded-full blur-lg"
           style={{ background: 'radial-gradient(circle, rgba(255,77,61,0.95), rgba(255,176,32,0.7) 45%, transparent 72%)' }} />
      <div className="corner-bracket absolute left-[32%] top-[12%] h-[74%] w-[38%]" />
      <span className="mono absolute left-2 top-2 text-[0.625rem] font-bold text-sentinel-acid">HEATMAP</span>
    </div>
  )
}

function AudioVisual() {
  const bars = Array.from({ length: 32 }, (_, i) => 0.25 + 0.75 * Math.abs(Math.sin(i * 0.55) * Math.cos(i * 0.21)))
  return (
    <div className="flex h-full items-end gap-[3px] rounded-md border-2 border-[#191919] px-3 pb-3 pt-6" style={{ background: '#191919' }}>
      {bars.map((b, i) => {
        const flagged = i >= 18 && i <= 24
        return (
          <span key={i} className="eq-bar flex-1"
                style={{ height: `${b * 100}%`, animationDelay: `${(i % 8) * 0.08}s`, background: flagged ? '#ff4d3d' : 'var(--acid)' }} />
        )
      })}
    </div>
  )
}

function VideoVisual() {
  return (
    <div className="flex h-full items-stretch gap-1.5 rounded-md border-2 border-[#191919] p-2" style={{ background: '#191919' }}>
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="relative flex-1 overflow-hidden rounded-sm"
             style={{ background: '#28282b', outline: i === 2 ? '2px solid #ff4d3d' : '1px solid #444449' }}>
          <span className="absolute left-1/2 top-[26%] h-[38%] w-[52%] -translate-x-1/2 rounded-full"
                style={{ background: i === 2 ? 'rgba(255,77,61,0.65)' : 'rgba(35,248,113,0.35)' }} />
          <span className="mono absolute bottom-1 left-1 text-[0.5rem] text-[#a7a7ab]">{String(i * 12).padStart(2, '0')}s</span>
        </div>
      ))}
    </div>
  )
}

const VISUALS = { image: ImageVisual, audio: AudioVisual, video: VideoVisual }

function ModalityCard({ m, idx, wide }) {
  const Icon = m.icon
  const Visual = VISUALS[m.id]
  return (
    <motion.div {...reveal(idx * 0.08)} className={wide ? 'md:col-span-2' : ''}>
      <Spotlight className="h-full !rounded-2xl !border-2 p-6 sm:p-8" color={m.shadow} bg={m.bg} fg={m.fg}>
        <div className={`grid h-full gap-6 ${wide ? 'md:grid-cols-[1fr_1.15fr] md:items-stretch' : ''}`}>
          <div className="flex flex-col">
            <div className="flex items-center justify-between">
              <span className="grid h-12 w-12 place-items-center rounded-md border-2 border-[#191919] bg-[#191919] text-sentinel-acid">
                <Icon size={22} />
              </span>
              <span className="mono text-[0.6875rem] font-bold uppercase tracking-wider opacity-70">{m.kicker}</span>
            </div>
            <Scramble as="h3" text={m.label}
                      className="wide mt-6 block text-[clamp(1.75rem,3vw,2.75rem)] font-black uppercase leading-none tracking-tight" />
            <p className="mt-3 flex-1 text-[1rem] font-medium leading-relaxed opacity-85">{m.body}</p>
            <p className="mt-5 border-t-2 border-[#191919] pt-4 text-[0.875rem] leading-relaxed">
              <span className="mono mr-2 rounded-sm bg-[#191919] px-1.5 py-0.5 text-[0.625rem] font-bold uppercase text-sentinel-acid">Limit</span>
              {m.limit}
            </p>
          </div>
          <div className={wide ? 'min-h-[12rem]' : 'h-32'} aria-hidden="true"><Visual /></div>
        </div>
      </Spotlight>
    </motion.div>
  )
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function Landing() {
  const stageRef = useRef(null)

  return (
    <div className="relative">
      {/* ══════════════════════════════ HERO ══════════════════════════════ */}
      <section className="relative grid min-h-[calc(100svh-4rem)] items-center gap-10 pb-16 pt-2 lg:grid-cols-[1.15fr_1fr]">
        <div className="relative z-10">
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease }}
            className="mono inline-flex items-center gap-2 rounded-md border-2 px-3 py-1.5 text-[0.75rem] font-bold uppercase"
            style={{ borderColor: 'var(--border-strong)' }}>
            <span className="led-critical" /> Live · deepfake detection for image, audio &amp; video
          </motion.div>

          <h1 className="wide mt-8 font-black uppercase text-ink-primary"
              style={{ fontSize: 'clamp(3.25rem, 8.4vw, 8.75rem)', lineHeight: 0.86, letterSpacing: '-0.06em' }}>
            <KineticLine words={[{ text: 'Is it' }]} delay={0.1} />
            <KineticLine
              words={[{ text: 'real?', className: 'glitch serif-i normal-case text-gradient !tracking-[-0.03em] text-[1.18em]', glitch: true }]}
              delay={0.22} />
            <KineticLine words={[{ text: 'Look' }, { text: 'closer.', className: 'text-outline-strong' }]} delay={0.36} />
          </h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.6, ease }}
            className="mt-8 text-ink-secondary"
            style={{ fontSize: 'clamp(1.0625rem, 1.25vw, 1.25rem)', maxWidth: '44ch', lineHeight: 1.55 }}
          >
            Upload a photo, voice clip or video. <strong className="text-ink-primary">DeepSentinel</strong> runs
            deepfake detectors on it, shows you <span className="highlight px-0.5 text-ink-primary">the evidence behind the score</span>,
            and tells you plainly when it can&apos;t be sure.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.75, ease }}
            className="mt-10 flex flex-wrap items-center gap-4"
          >
            <Magnetic>
              <Link to="/analyse" className="btn-glow btn-lg group">
                Analyse a file
                <ArrowRight size={18} className="transition-transform duration-200 group-hover:translate-x-1" />
              </Link>
            </Magnetic>
            <Magnetic strength={0.25}>
              <Link to="/how-it-works" className="btn-neon btn-lg">How it works</Link>
            </Magnetic>
          </motion.div>
        </div>

        {/* Scanner monitor with draggable stickers around it */}
        <motion.div ref={stageRef}
          initial={{ opacity: 0, y: 40, rotate: 3 }} animate={{ opacity: 1, y: 0, rotate: 0 }} transition={{ duration: 0.9, delay: 0.2, ease }}
          className="relative mx-auto w-full max-w-[36rem] p-4 sm:p-8">
          <div className="overflow-hidden rounded-2xl border-2 border-[#191919]"
               style={{ background: 'var(--ink)', boxShadow: '12px 12px 0 var(--acid)' }}>
            <div className="mono flex items-center justify-between border-b-2 border-[#333337] px-4 py-2.5 text-[0.6875rem] font-bold uppercase"
                 style={{ background: '#28282b', color: '#a7a7ab' }}>
              <span className="flex items-center gap-2"><span className="led-critical" /> sentinel-cam_01</span>
              <span style={{ color: 'var(--acid)' }}>REC ● seam check</span>
            </div>
            <div className="relative aspect-[4/5] cursor-crosshair">
              <ScanField />
              <span className="mono pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 whitespace-nowrap text-[0.625rem] uppercase tracking-wider text-[#8a8a92]">
                move the loupe · illustration, not a scan
              </span>
            </div>
          </div>

          {STICKERS.map((s, i) => (
            <motion.span key={s.text}
              drag dragConstraints={stageRef} dragElastic={0.25} dragMomentum
              whileHover={{ scale: 1.08 }} whileDrag={{ scale: 1.15, rotate: 0, zIndex: 20 }}
              initial={{ opacity: 0, scale: 0.4 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ type: 'spring', stiffness: 300, damping: 14, delay: 0.9 + i * 0.12 }}
              className={`sticker absolute z-10 cursor-grab touch-none select-none active:cursor-grabbing ${s.pos}`}
              style={{ '--r': `${s.r}deg`, background: s.bg }}
              aria-hidden="true">
              {s.text}
            </motion.span>
          ))}
        </motion.div>
      </section>

      {/* ══════════════════════════ CROSSED TAPES ═════════════════════════ */}
      <div className="bleed relative z-10 my-6 h-[9rem] sm:h-[11rem]">
        <Marquee items={TAPE_A} tone="acid" tilt={-3} className="absolute inset-x-[-2%] top-6" />
        <Marquee items={TAPE_B} tone="ink" tilt={2.5} reverse className="absolute inset-x-[-2%] top-16 sm:top-20" />
      </div>

      {/* ══════════════════════════ MANIFESTO (scroll-lit words) ════════ */}
      <Manifesto />

      {/* ══════════════════════════ MODALITIES ═══════════════════════════ */}
      <section className="py-20 lg:py-28">
        <SectionHead
          index="01"
          label="What it checks"
          title={<>One box.<br /><span className="serif-i normal-case text-gradient">three</span> kinds of media.</>}
          sub="Each media type gets its own detectors, because a cloned voice and a swapped face leave very different traces."
        />
        <div className="grid gap-7 md:grid-cols-2">
          <ModalityCard m={MODALITIES[0]} idx={0} wide />
          <ModalityCard m={MODALITIES[1]} idx={1} />
          <ModalityCard m={MODALITIES[2]} idx={2} />
        </div>
      </section>

      {/* ══════════════════════════ LAB A: look-alike text ══════════════ */}
      <motion.section {...reveal()} className="pb-10 lg:pb-16">
        <HomoglyphLab />
      </motion.section>

      {/* ══════════════════════════ SCAN FILM (pinned, horizontal) ═══════ */}
      <ScanFilm />

      {/* ══════════════════════════ LAB B: live fingerprint ═════════════ */}
      <motion.section {...reveal()} className="pb-20 lg:pb-28">
        <FingerprintLab />
      </motion.section>

      {/* ══════════════════════════ PRINCIPLES (full-bleed pine) ══════════ */}
      <section className="bleed border-y-2 border-[#191919] py-20 lg:py-28" style={{ background: 'var(--pine)', color: '#ececed' }}>
        <div className="mx-auto max-w-content px-4 sm:px-6 lg:px-10">
          <SectionHead
            dark
            index="03"
            label="Honest by design"
            title={<>A detector you can <span className="serif-i normal-case" style={{ color: 'var(--acid)' }}>argue</span> with.</>}
            sub="Scores come with the evidence behind them and the limits of the models that produced them."
          />
          <div className="border-t-2" style={{ borderColor: 'var(--sea)' }}>
            {PRINCIPLES.map((p, i) => (
              <motion.div key={p.title} {...reveal(i * 0.06)}
                className="group -mx-4 grid items-center gap-4 border-b-2 px-4 py-8 transition-colors duration-200 hover:bg-[var(--acid)] hover:text-[#191919] md:grid-cols-[5rem_1.3fr_1fr] md:gap-10 md:py-10"
                style={{ borderColor: 'var(--sea)' }}>
                <span className="grid h-14 w-14 place-items-center rounded-md border-2 border-[#191919] bg-[var(--acid)] text-[#191919] transition-transform duration-300 group-hover:rotate-12 group-hover:scale-110 group-hover:bg-[#191919] group-hover:text-[var(--acid)]">
                  <p.icon size={24} />
                </span>
                <h3 className="wide font-black uppercase" style={{ fontSize: 'clamp(1.5rem, 3vw, 2.75rem)', letterSpacing: '-0.045em', lineHeight: 0.95 }}>
                  {p.title}
                </h3>
                <p className="text-[1.0625rem] leading-relaxed opacity-80">{p.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════ CTA (full-bleed acid) ═════════════════ */}
      <section className="bleed relative overflow-hidden border-b-2 border-[#191919] py-24 sm:py-32" style={{ background: 'var(--acid)', color: '#191919' }}>
        <div className="pointer-events-none absolute inset-0 opacity-30"
             style={{ backgroundImage: 'radial-gradient(#191919 1.2px, transparent 1.2px)', backgroundSize: '22px 22px' }} aria-hidden="true" />
        <motion.div {...reveal()} className="relative mx-auto max-w-content px-4 text-center sm:px-6 lg:px-10">
          <span className="sticker" style={{ '--r': '-4deg', background: '#191919', color: 'var(--acid)', boxShadow: '3px 3px 0 #ececed' }}>Your turn</span>
          <h2 className="wide mt-8 font-black uppercase"
              style={{ fontSize: 'clamp(3rem, 9vw, 9rem)', lineHeight: 0.85, letterSpacing: '-0.065em' }}>
            Got something<br /><span className="serif-i normal-case !tracking-[-0.03em]">suspicious?</span>
          </h2>
          <p className="mx-auto mt-8 max-w-xl text-[1.125rem] font-semibold">
            Drop it in. You&apos;ll get a verdict, the evidence behind it and a PDF report.
          </p>
          <div className="mt-10 flex justify-center">
            <Magnetic>
              <Link to="/analyse" className="btn btn-lg group border-[#191919] bg-[#191919] uppercase text-[var(--acid)] shadow-[6px_6px_0_#ececed] hover:-translate-x-1 hover:-translate-y-1 hover:shadow-[10px_10px_0_#ececed]"
                    style={{ fontStretch: '115%', fontWeight: 800 }}>
                Start a scan
                <ArrowRight size={18} className="transition-transform duration-200 group-hover:translate-x-1" />
              </Link>
            </Magnetic>
          </div>
        </motion.div>
      </section>

      <div className="mt-12">
        <Notice tone="warn" title="Automated assessment only. Not forensic or legal evidence.">
          Detection scores are statistical. Compression, resizing and very low resolution can change
          them, and no detector catches every generator. Treat a result as a lead to check, not proof.
        </Notice>
      </div>
    </div>
  )
}
