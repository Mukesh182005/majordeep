import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import Marquee from '../components/fx/Marquee'
import Scramble from '../components/fx/Scramble'
import {
  ApiSwitchboard, ArchitectureStack, DeployMap, Glossary, ObjectivesBoard, PartDivider,
  PipelineModules, ProblemSection, SecurityGrid, TestingBoard, Timeline,
} from '../components/howitworks/Sections'
import { Faq, NumbersBoard, ProjectExplorer } from '../components/howitworks/MoreSections'
import {
  AttackRadial, AudioDumbbell, AudioWindows, DevTestFlow, ModelScale, SystemMap, VideoWaffles,
} from '../components/howitworks/Visuals'
import {
  AlertTriangle, ArrowRight, Check, Clock, Cpu, Database, FileText, GitBranch,
  Hash, Image as ImageIcon, Lock, Network, ShieldQuestion, Upload, Video as VideoIcon, Waveform, X,
} from '../components/ui/Icons'

// Every figure on this page is copied from the project's own records, and the
// file it comes from is printed next to it. Main sources:
//   docs/models/MODEL_CARD.md, docs/research/EVALUATION.md,
//   docs/research/DATASETS.md, KNOWN_ISSUES.md, results/*.json.

const CHAPTERS = [
  ['problem', 'The problem'],
  ['objectives', 'Objectives'],
  ['architecture', 'Architecture'],
  ['systemmap', 'System map'],
  ['journey', 'Journey of a file'],
  ['band', 'The verdict band'],
  ['decide', 'How a verdict is made'],
  ['engines', 'Three engines'],
  ['pipelines', 'Inside the pipelines'],
  ['api', 'The API'],
  ['security', 'Security & privacy'],
  ['results', 'How well it works'],
  ['deepdive', 'Charts deep-dive'],
  ['speed', 'Speed'],
  ['rejected', 'Tried & rejected'],
  ['timeline', 'Timeline'],
  ['data', 'Datasets'],
  ['limits', 'Known limits'],
  ['explorer', 'Project explorer'],
  ['deploy', 'Deployment'],
  ['testing', 'Testing'],
  ['glossary', 'Glossary'],
  ['faq', 'FAQ'],
  ['stack', 'Under the hood'],
]

const ease = [0.2, 0.9, 0.3, 1]
const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.6, delay, ease },
})

function Source({ children }) {
  return (
    <p className="mono mt-3 text-[0.6875rem] leading-relaxed text-ink-muted">
      <span className="mr-1 font-bold text-accent">SRC</span>{children}
    </p>
  )
}

function Chapter({ id, kicker, title, intro, children, dark = false }) {
  const num = String(CHAPTERS.findIndex(([c]) => c === id) + 1).padStart(2, '0')
  return (
    <section id={id} className={`scroll-mt-28 ${dark ? 'bleed border-y-2 border-[#191919] py-20' : 'py-16 lg:py-24'}`}
             style={dark ? { background: 'var(--pine)', color: '#ececed' } : undefined}>
      <div className={dark ? 'mx-auto max-w-content px-4 sm:px-6 lg:px-10' : ''}>
        <motion.div {...reveal()} className="mb-10 grid gap-4 lg:grid-cols-[auto_1fr] lg:gap-10">
          <span className="wide text-outline font-black leading-none" style={{ fontSize: 'clamp(4rem, 8vw, 7rem)', WebkitTextStrokeColor: dark ? '#246a48' : undefined }}>
            {num}
          </span>
          <div className="self-end">
            <span className="mono text-[0.75rem] font-bold uppercase tracking-wider" style={{ color: dark ? 'var(--acid)' : 'var(--accent)' }}>
              {'// '}{kicker}
            </span>
            <h2 className="wide mt-2 font-black uppercase" style={{ fontSize: 'clamp(2rem, 4.6vw, 4rem)', lineHeight: 0.92, letterSpacing: '-0.05em' }}>
              {title}
            </h2>
            {intro && (
              <p className="mt-4 max-w-2xl text-[1.0625rem] leading-relaxed" style={{ color: dark ? '#a7e1c5' : 'var(--text-secondary)' }}>
                {intro}
              </p>
            )}
          </div>
        </motion.div>
        {children}
      </div>
    </section>
  )
}

// ─── 01 · Journey flowchart ──────────────────────────────────────────────────

const FLOW = {
  upload: { icon: Upload, title: 'Upload', tag: 'Browser → API',
    body: 'You drop a file on the Analyse page. The API checks the type is enabled, the size is under the limit, and audio or video is not longer than the allowed seconds, before anything is stored.' },
  hash: { icon: Hash, title: 'Fingerprint', tag: 'SHA-256',
    body: 'A SHA-256 hash of the bytes is computed while the file is written. The same hash is printed in the PDF report, so the report can be matched to one exact file.' },
  queue: { icon: Network, title: 'Queue', tag: 'Celery + Redis',
    body: 'The job goes onto a Redis queue and a Celery worker picks it up. Only the worker holds the models; the web server stays light. Progress streams to your browser over a WebSocket.' },
  route: { icon: GitBranch, title: 'Router', tag: 'By media type',
    body: 'The worker sends the file to the pipeline for its media type: image, audio or video. Each pipeline has its own detectors, because each kind of fake leaves different traces.' },
  image: { icon: ImageIcon, title: 'Image engine', tag: 'Scene ensemble',
    body: 'SwinV2 and Community Forensics ViT detectors score the whole picture, fused as a weighted mean of log-odds. Metadata and C2PA provenance are read; TruFor marks possibly edited regions but does not vote.' },
  audio: { icon: Waveform, title: 'Audio engine', tag: 'pellav2 · LCNN',
    body: 'pellav2 (w2v-BERT 2.0) scores up to eight 4-second windows. If it cannot run, the LCNN trained on ASVspoof 2019 LA decides. Glottal, mains-hum and splice checks are shown as unvalidated notes.' },
  video: { icon: VideoIcon, title: 'Video engine', tag: 'GenD face model',
    body: 'Frames are sampled at 1 fps (up to 32). GenD scores each face crop and the face score is the mean over frames; scene detectors check 8 evenly spaced frames for fully generated content.' },
  verdict: { icon: ShieldQuestion, title: 'Verdict rule', tag: 'With an uncertainty band',
    body: 'The score is compared with thresholds chosen on development data. Between them is a band where the answer is INCONCLUSIVE, so borderline files are never forced into real or fake.' },
  report: { icon: FileText, title: 'Report', tag: 'Result page + PDF',
    body: 'The result page shows the verdict, the evidence and the limits. The PDF carries the same, plus the file hash. Delete a scan and its upload, evidence and report are removed.' },
}

function FlowNode({ id, active, onPick, accent = 'var(--acid)' }) {
  const n = FLOW[id]
  const on = active === id
  return (
    <button onClick={() => onPick(id)} aria-pressed={on}
      className="group relative w-full rounded-xl border-2 p-3 text-left transition-all duration-200 sm:p-4"
      style={{
        borderColor: on ? '#191919' : 'var(--border-strong)',
        background: on ? accent : 'var(--surface-1)',
        color: on ? '#191919' : 'var(--text-primary)',
        boxShadow: on ? '6px 6px 0 var(--pop)' : 'none',
        transform: on ? 'translate(-3px,-3px)' : 'none',
      }}>
      <span className="flex items-center gap-2.5">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border-2"
              style={{ borderColor: on ? '#191919' : 'var(--border-strong)', background: on ? '#191919' : 'var(--surface-2)', color: on ? accent : 'var(--accent)' }}>
          <n.icon size={17} />
        </span>
        <span className="min-w-0">
          <span className="wide block text-[0.9375rem] font-black uppercase leading-tight">{n.title}</span>
          <span className="mono block truncate text-[0.625rem] font-bold uppercase opacity-70">{n.tag}</span>
        </span>
      </span>
    </button>
  )
}

/** Vertical connector with a light pulse running down it. */
function Wire({ delay = 0 }) {
  return (
    <div className="relative mx-auto h-8 w-[3px] overflow-hidden" style={{ background: 'var(--border-strong)' }} aria-hidden="true">
      <span className="flow-pulse absolute inset-x-0 top-0 h-3" style={{ background: 'var(--acid)', animationDelay: `${delay}s` }} />
    </div>
  )
}

function JourneyFlow() {
  const [active, setActive] = useState('upload')
  const order = Object.keys(FLOW)

  // Auto-advance until the visitor takes over.
  const [auto, setAuto] = useState(true)
  useEffect(() => {
    if (!auto || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    const t = window.setInterval(() => setActive((a) => order[(order.indexOf(a) + 1) % order.length]), 3200)
    return () => window.clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auto])

  const pick = (id) => { setAuto(false); setActive(id) }
  const n = FLOW[active]

  return (
    <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr] lg:items-start">
      <motion.div {...reveal()} className="rounded-2xl border-2 border-[#191919] p-4 sm:p-6"
                  style={{ background: 'var(--surface-2)', backgroundImage: 'linear-gradient(var(--grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--grid-line) 1px, transparent 1px)', backgroundSize: '24px 24px' }}>
        <div className="mx-auto max-w-md space-y-0">
          {['upload', 'hash', 'queue', 'route'].map((id, i) => (
            <div key={id}>
              <FlowNode id={id} active={active} onPick={pick} />
              <Wire delay={i * 0.35} />
            </div>
          ))}
        </div>
        {/* three lanes */}
        <div className="relative">
          <div className="absolute left-[16.6%] right-[16.6%] top-0 h-[3px]" style={{ background: 'var(--border-strong)' }} aria-hidden="true" />
          <div className="grid grid-cols-3 gap-2 sm:gap-3">
            {[['image', 'var(--acid)'], ['audio', 'var(--teal)'], ['video', 'var(--mint)']].map(([id, c], i) => (
              <div key={id}>
                <Wire delay={1.4 + i * 0.15} />
                <FlowNode id={id} active={active} onPick={pick} accent={c} />
                <Wire delay={1.9 + i * 0.15} />
              </div>
            ))}
          </div>
          <div className="absolute bottom-0 left-[16.6%] right-[16.6%] h-[3px]" style={{ background: 'var(--border-strong)' }} aria-hidden="true" />
        </div>
        <div className="mx-auto max-w-md">
          <Wire delay={2.4} />
          <FlowNode id="verdict" active={active} onPick={pick} accent="#ffb020" />
          <Wire delay={2.8} />
          <FlowNode id="report" active={active} onPick={pick} />
        </div>
      </motion.div>

      <div className="lg:sticky lg:top-28">
        <motion.div key={active} initial={{ opacity: 0, x: 24, rotate: 1 }} animate={{ opacity: 1, x: 0, rotate: 0 }} transition={{ duration: 0.4, ease }}
          className="rounded-2xl border-2 border-[#191919] p-6 text-[#191919] sm:p-8" style={{ background: 'var(--mint-soft)', boxShadow: '10px 10px 0 var(--acid)' }}>
          <div className="flex items-center justify-between">
            <span className="mono text-[0.75rem] font-bold uppercase">Step {order.indexOf(active) + 1} / {order.length}</span>
            <span className="sticker" style={{ '--r': '3deg', background: '#191919', color: 'var(--acid)', boxShadow: '3px 3px 0 #ececed' }}>{n.tag}</span>
          </div>
          <span className="mt-6 grid h-16 w-16 place-items-center rounded-xl border-2 border-[#191919] bg-[#191919] text-[var(--acid)]">
            <n.icon size={30} />
          </span>
          <h3 className="wide mt-5 text-4xl font-black uppercase leading-none tracking-tight">{n.title}</h3>
          <p className="mt-4 text-[1.0625rem] font-medium leading-relaxed">{n.body}</p>
          <div className="mt-6 flex gap-1.5">
            {order.map((id) => (
              <button key={id} onClick={() => pick(id)} aria-label={FLOW[id].title}
                      className="h-2.5 flex-1 rounded-sm border border-[#191919] transition-colors"
                      style={{ background: id === active ? '#191919' : 'transparent' }} />
            ))}
          </div>
          <p className="mono mt-4 text-[0.6875rem] font-bold uppercase opacity-60">{auto ? 'Auto-playing · click any step to explore' : 'Click any step'}</p>
        </motion.div>
      </div>
    </div>
  )
}

// ─── 02 · Verdict band simulator ─────────────────────────────────────────────

const RULES = {
  image: { label: 'Image', low: 0.02, high: 0.58, lowName: 'No manipulation detected', highName: 'Likely manipulated',
    note: 'Shown for a file without camera metadata, which is most uploads. With camera metadata the low cut is 0.42 (0.5 − 0.08).',
    src: 'backend/app/config.py (fake_threshold, uncertain_band, image_authentic_max_prob_without_camera)' },
  audio: { label: 'Audio', low: 0.42, high: 0.58, lowName: 'No manipulation detected', highName: 'Likely AI-generated',
    note: 'pellav2: the authors’ 0.5 cut with the platform’s ±0.08 band around it.',
    src: 'docs/models/MODEL_CARD.md · Audio · Output (paper/config/pellav2_verdict_config.json)' },
}

function BandSimulator() {
  const [mode, setMode] = useState('image')
  const [score, setScore] = useState(0.35)
  const r = RULES[mode]
  const zone = score >= r.high ? 'fake' : score < r.low ? 'real' : 'unsure'
  const zoneMeta = {
    real: { name: r.lowName, color: 'var(--acid)' },
    unsure: { name: 'Inconclusive', color: '#ffb020' },
    fake: { name: r.highName, color: '#ff4d3d' },
  }[zone]

  return (
    <motion.div {...reveal()} className="overflow-hidden rounded-2xl border-2 border-[#191919]" style={{ background: '#ececed', color: '#191919', boxShadow: '10px 10px 0 var(--acid)' }}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-[#191919] p-4 sm:px-8">
        <span className="mono text-[0.75rem] font-bold uppercase">Verdict simulator · drag the score</span>
        <div className="flex gap-2" role="tablist">
          {Object.entries(RULES).map(([k, v]) => (
            <button key={k} role="tab" aria-selected={mode === k} onClick={() => setMode(k)}
                    className="mono rounded-md border-2 border-[#191919] px-3 py-1 text-[0.75rem] font-bold uppercase transition-all"
                    style={{ background: mode === k ? '#191919' : 'transparent', color: mode === k ? 'var(--acid)' : '#191919' }}>
              {v.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[1.4fr_1fr] lg:items-center">
        <div>
          {/* the band */}
          <div className="relative h-16 overflow-hidden rounded-lg border-2 border-[#191919]">
            <motion.div className="absolute inset-y-0 left-0" animate={{ width: `${r.low * 100}%` }} transition={{ duration: 0.5, ease }} style={{ background: 'var(--acid)' }} />
            <motion.div className="absolute inset-y-0" animate={{ left: `${r.low * 100}%`, width: `${(r.high - r.low) * 100}%` }} transition={{ duration: 0.5, ease }}
                        style={{ background: 'repeating-linear-gradient(45deg, #ffb020 0 10px, #ffc657 10px 20px)' }} />
            <motion.div className="absolute inset-y-0 right-0" animate={{ left: `${r.high * 100}%` }} transition={{ duration: 0.5, ease }} style={{ background: '#ff4d3d' }} />
            <motion.div className="absolute inset-y-[-2px] w-1.5 bg-[#191919]" animate={{ left: `calc(${score * 100}% - 3px)` }} transition={{ type: 'spring', stiffness: 400, damping: 30 }} />
          </div>
          <input type="range" min="0" max="1" step="0.005" value={score} onChange={(e) => setScore(Number(e.target.value))}
                 aria-label="Model score" className="band-range mt-4 w-full" />
          <div className="mono mt-1 flex justify-between text-[0.6875rem] font-bold">
            <span>0.00</span>
            <span>low cut {r.low.toFixed(2)}</span>
            <span>high cut {r.high.toFixed(2)}</span>
            <span>1.00</span>
          </div>
          <p className="mt-5 text-[0.9375rem] leading-relaxed">{r.note}</p>
          <p className="mono mt-2 text-[0.6875rem] opacity-60">SRC {r.src}</p>
        </div>

        <motion.div key={zone + mode} initial={{ scale: 0.9, rotate: -4, opacity: 0 }} animate={{ scale: 1, rotate: -2, opacity: 1 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 18 }}
                    className="rounded-xl border-2 border-[#191919] p-6 text-center" style={{ background: zoneMeta.color, boxShadow: '6px 6px 0 #191919' }}>
          <span className="mono text-[0.75rem] font-bold uppercase">Score {score.toFixed(3)} →</span>
          <p className="wide mt-2 text-[clamp(1.5rem,2.6vw,2.25rem)] font-black uppercase leading-none">{zoneMeta.name}</p>
        </motion.div>
      </div>
    </motion.div>
  )
}

// ─── 03 · Engines ────────────────────────────────────────────────────────────

const ENGINES = [
  {
    id: 'image', icon: ImageIcon, title: 'Image', color: 'var(--acid)',
    rows: [
      ['Verdict models', 'haywoodsloan SwinV2 (weight 0.75) + Community Forensics ViT-S/384 (weight 4) + the same ViT fine-tuned here on FLUX.2, GPT Image 2 and Nano Banana 2 (weight 4)'],
      ['Fusion', 'Weighted mean of log-odds'],
      ['Shown, no vote', 'TruFor edit heatmap; EXIF and C2PA provenance; the project’s own face-crop model (off: it memorised its data)'],
    ],
    src: 'docs/models/MODEL_CARD.md · Image',
  },
  {
    id: 'audio', icon: Waveform, title: 'Audio', color: 'var(--teal)',
    rows: [
      ['Verdict model', 'pellav2: w2v-BERT 2.0 encoder, 580.5 M parameters, pretrained by its authors (MIT)'],
      ['Fallback', 'LCNN, 144,065 parameters, trained here on ASVspoof 2019 LA (25,380 training utterances)'],
      ['Shown, no vote', 'Glottal flow, voice quality, mains hum (ENF), splice timeline: all AUCs 0.41–0.57 on dev'],
    ],
    src: 'docs/models/MODEL_CARD.md · Audio Detector',
  },
  {
    id: 'video', icon: VideoIcon, title: 'Video', color: 'var(--mint)',
    rows: [
      ['Face model', 'GenD: CLIP ViT-L/14 with a tuned linear head (WACV 2026, MIT), pretrained on FaceForensics++'],
      ['Sampling', '1 frame per second, up to 32 frames; face score = mean over frames'],
      ['Shown, no vote', 'rPPG, LipForensics, generator profile match, optical flow'],
    ],
    src: 'docs/models/MODEL_CARD.md · Video Detector',
  },
]

// ─── 04 · Results charts ────────────────────────────────────────────────────

function Bar({ label, value, max = 100, color = 'var(--acid)', suffix = '%', delay = 0, note }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 text-[0.875rem]">
        <span className="font-semibold">{label}</span>
        <span className="wide tnum font-black">{value}{suffix}</span>
      </div>
      <div className="mt-1.5 h-4 overflow-hidden rounded-sm border-2 border-[#191919]" style={{ background: 'var(--surface-3)' }}>
        <motion.div className="h-full" style={{ background: color }}
                    initial={{ width: 0 }} whileInView={{ width: `${(value / max) * 100}%` }} viewport={{ once: true }}
                    transition={{ duration: 1, delay, ease }} />
      </div>
      {note && <p className="mt-1 text-[0.75rem] text-ink-muted">{note}</p>}
    </div>
  )
}

function ChartCard({ title, children, src, tone = 'var(--surface-1)' }) {
  return (
    <motion.div {...reveal()} className="rounded-2xl border-2 border-[#191919] p-6" style={{ background: tone, boxShadow: '6px 6px 0 #000' }}>
      <h3 className="wide text-lg font-black uppercase leading-tight tracking-tight">{title}</h3>
      <div className="mt-5 space-y-4">{children}</div>
      <Source>{src}</Source>
    </motion.div>
  )
}

const GENERATORS = [
  ['DALL·E 2', 106, 106], ['DALL·E 3', 102, 104], ['Firefly', 108, 108], ['GLIDE', 90, 95], ['Midjourney v5', 102, 104],
  ['SD 1.3', 99, 99], ['SD 1.4', 94, 94], ['SD 2', 103, 108], ['SDXL', 100, 101],
  ['FLUX.2', 139, 194], ['Qwen Image 2.1', 458, 900], ['GPT Image 2', 46, 195], ['Nano Banana 2', 8, 192],
]

function GeneratorChart() {
  return (
    <motion.div {...reveal()} className="rounded-2xl border-2 border-[#191919] p-6" style={{ background: 'var(--surface-1)', boxShadow: '6px 6px 0 #000' }}>
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h3 className="wide text-lg font-black uppercase leading-tight tracking-tight">AI images caught, per generator</h3>
        <span className="mono text-[0.6875rem] text-ink-muted">called MANIPULATED / tested</span>
      </div>
      <div className="mt-6 flex h-64 items-end gap-1.5 sm:gap-3">
        {GENERATORS.map(([g, hit, n], i) => {
          const pct = (hit / n) * 100
          const color = pct >= 90 ? 'var(--acid)' : pct >= 40 ? '#ffb020' : '#ff4d3d'
          return (
            <div key={g} className="group flex h-full flex-1 flex-col items-center justify-end">
              <span className="mono mb-1 text-[0.5625rem] font-bold opacity-0 transition-opacity group-hover:opacity-100 sm:text-[0.625rem]">{hit}/{n}</span>
              <motion.div className="w-full rounded-t-sm border-2 border-b-0 border-[#191919]" style={{ background: color }}
                          initial={{ height: 0 }} whileInView={{ height: `${pct}%` }} viewport={{ once: true }}
                          transition={{ duration: 0.9, delay: i * 0.05, ease }} />
            </div>
          )
        })}
      </div>
      <div className="flex gap-1.5 border-t-2 border-[#191919] pt-2 sm:gap-3">
        {GENERATORS.map(([g]) => (
          <span key={g} className="mono flex-1 truncate text-center text-[0.5rem] font-bold uppercase leading-tight text-ink-muted sm:text-[0.5625rem]" title={g}
                style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: '5.5rem' }}>{g}</span>
        ))}
      </div>
      <p className="mt-4 text-[0.875rem] leading-relaxed text-ink-secondary">
        Older generators are almost always caught. The newest ones are the weak point: GPT Image 2 and Nano Banana 2 are
        mostly returned as <strong>inconclusive</strong>, not flagged. Hover a bar for the count.
      </p>
      <Source>docs/research/EVALUATION.md §5 · evaluation/E2E-02/summary.json (per_group)</Source>
    </motion.div>
  )
}

const FIGURES = [
  ['audio_roc.png', 'Audio model ROC, ASVspoof 2019 LA eval', 'results/figures/audio_roc.png', -2],
  ['audio_codec_robustness.png', 'Audio model under MP3 and Opus re-encoding', 'results/figures/audio_codec_robustness.png', 1.5],
  ['audio_pipeline_verdicts.png', 'Audio verdicts end to end', 'results/figures/audio_pipeline_verdicts.png', 1],
  ['latency.png', 'Latency per modality, GPU vs CPU', 'results/figures/latency.png', -1.5],
]

// ─── 06 · Tried & rejected ──────────────────────────────────────────────────

const LOG = [
  { stamp: 'Retired', color: '#ff4d3d', title: 'Audio model trained on sine waves',
    body: 'The first audio checkpoint had been trained on generated NumPy tones, not speech. It was retired and replaced by an LCNN trained on ASVspoof 2019 LA.',
    src: 'docs/models/MODEL_CARD.md · Audio · Retired' },
  { stamp: 'Switched off', color: '#ffb020', title: 'A 99.98 % face model that only memorised',
    body: '144,000 of its 164,000 validation images were re-encoded copies of training faces. On real photos it flagged 21 % of real faces and 15 % of AI faces, so it no longer votes.',
    src: 'docs/models/MODEL_CARD.md · Face-crop GAN classifier' },
  { stamp: 'Fixed', color: 'var(--acid)', title: 'Two video heuristics overruled the evidence',
    body: 'LipForensics and a generator profile match forced 26 of 60 real videos to MANIPULATED. After they were stopped from forcing verdicts, 0 of 40 held-out real videos were.',
    src: 'docs/research/EVALUATION.md §6 · evaluation/VIDEO-GEND-01/summary.json' },
  { stamp: 'Rejected', color: '#ff4d3d', title: 'Image fine-tune v4',
    body: 'Caught far more of the newest generators (84.2 %) but called 2.0 % of real COCO photos manipulated. The rule fixed in advance was “no test set may get worse”, so it was not adopted.',
    src: 'docs/research/EVALUATION.md §5 · evaluation/COMMFOR-FT-02' },
  { stamp: 'Rejected', color: '#ff4d3d', title: 'Codec-hardened pellav2',
    body: 'Cut false alarms on ASVspoof 5 from 15.0 % to 4.0 %, but caught fewer fakes (77.0 % → 54.0 %). It missed the pre-set bar, so the original model stays.',
    src: 'docs/research/EVALUATION.md §5a · evaluation/E2E-03/summary.json' },
  { stamp: 'Removed', color: '#ffb020', title: 'Model names that were not real models',
    body: 'Early outputs named audio models that never ran and quoted forensic standards the tool does not meet. Both were removed from the API, the PDF and the interface.',
    src: 'KNOWN_ISSUES.md · Resolved' },
]

// ─── 07/08 · Datasets, limits, stack ────────────────────────────────────────

const DATASETS = [
  ['ASVspoof 2019 LA', 'Audio training, choices and test', 'Edinburgh DataShare · ODC-By 1.0'],
  ['ASVspoof 5 (eval sample)', 'Held-out audio test, 3,004 clips', 'Zenodo · ODC-By 1.0'],
  ['COCO val2017', 'Real photos for the image test', 'Flickr licences / CC BY 4.0'],
  ['Synthbuster', 'AI images from 9 generators', 'Zenodo · CC BY-NC-SA 4.0'],
  ['MLLM-Generated Images', 'Newest generators: fine-tune and test', 'see DATASETS.md'],
  ['DFD (Google / Jigsaw)', 'Video test: 200 real, 200 face swaps', 'Paid, consenting actors'],
  ['140k Real and Fake Faces', 'Face-crop model training (switched off)', 'Kaggle'],
]

const LIMITS = [
  ['Newest image generators', 'GPT Image 2 and Nano Banana 2 are mostly inconclusive, not flagged.', '#17'],
  ['MP3 breaks the fallback audio model', 'After MP3 encoding the LCNN called every genuine clip AI-generated.', '#14'],
  ['Neural and phone codecs', 'pellav2 called 15 % of genuine ASVspoof 5 speech AI-generated.', '#16'],
  ['Composites and local edits', 'Edits inside a real photo are shown on a heatmap but are not part of the verdict.', '#18'],
  ['Fully AI-generated video', 'No labelled set yet, so it has not been measured.', 'EVAL §6'],
  ['Real-world audio', 'The In-the-Wild test is still pending.', '#13'],
]

const STACK = [
  ['Frontend', 'React · Vite · Tailwind · Framer Motion', Cpu],
  ['API', 'FastAPI · SQLAlchemy · Alembic', Network],
  ['Jobs', 'Celery workers · Redis queue · WebSocket progress', Clock],
  ['Storage', 'PostgreSQL · retention clean-up for guest scans', Database],
  ['Models', 'PyTorch · Hugging Face · CUDA when available', GitBranch],
  ['Security', 'httpOnly cookie sessions · 5-minute signed links', Lock],
]

// ─── Page ───────────────────────────────────────────────────────────────────

function ChapterRail() {
  const [current, setCurrent] = useState(CHAPTERS[0][0])
  const [hidden, setHidden] = useState(false)
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return undefined
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) setCurrent(e.target.id)
    }, { rootMargin: '-40% 0px -55% 0px' })
    CHAPTERS.forEach(([id]) => { const el = document.getElementById(id); if (el) io.observe(el) })
    // Hide the rail once the footer scrolls in, so it never sits on top of it.
    const footer = document.querySelector('footer')
    const fo = new IntersectionObserver(([e]) => setHidden(e.isIntersecting))
    if (footer) fo.observe(footer)
    return () => { io.disconnect(); fo.disconnect() }
  }, [])
  return (
    <nav className="fixed left-3 top-1/2 z-20 hidden -translate-y-1/2 transition-opacity duration-300 2xl:block" aria-label="Chapters"
         style={{ opacity: hidden ? 0 : 1, pointerEvents: hidden ? 'none' : undefined }}>
      <ol className="space-y-1.5">
        {CHAPTERS.map(([id, label], i) => (
          <li key={id}>
            <a href={`#${id}`} className="group flex items-center gap-2">
              <span className="mono grid h-7 w-7 place-items-center rounded-md border-2 text-[0.625rem] font-bold transition-all"
                    style={{ borderColor: current === id ? '#191919' : 'var(--border-strong)', background: current === id ? 'var(--acid)' : 'var(--surface-1)', color: current === id ? '#191919' : 'var(--text-muted)' }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              <span className="mono whitespace-nowrap rounded-sm bg-[#191919] px-1.5 py-0.5 text-[0.625rem] font-bold uppercase text-[var(--acid)] opacity-0 transition-opacity group-hover:opacity-100">
                {label}
              </span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  )
}

export default function HowItWorks() {
  const heroRef = useRef(null)

  return (
    <div className="relative">
      <ChapterRail />

      {/* ══════════ HERO: case-file cover ══════════ */}
      <section ref={heroRef} id="overview" className="relative overflow-hidden rounded-2xl border-2 border-[#191919] p-8 sm:p-12"
               style={{ background: 'var(--pine)', color: '#ececed', boxShadow: '12px 12px 0 var(--acid)' }}>
        <div className="pointer-events-none absolute inset-0"
             style={{ backgroundImage: 'linear-gradient(rgba(167,225,197,.07) 1px, transparent 1px), linear-gradient(90deg, rgba(167,225,197,.07) 1px, transparent 1px)', backgroundSize: '32px 32px' }} />
        <span className="mono pointer-events-none absolute -right-6 top-10 rotate-12 rounded-md border-4 px-4 py-1 text-2xl font-bold uppercase opacity-80 sm:text-4xl"
              style={{ borderColor: 'var(--acid)', color: 'var(--acid)' }} aria-hidden="true">
          Case file
        </span>

        <div className="relative z-10 max-w-4xl">
          <span className="sticker" style={{ '--r': '-2deg' }}>How it works</span>
          <h1 className="wide mt-6 font-black uppercase" style={{ fontSize: 'clamp(2.25rem, 5.6vw, 5rem)', lineHeight: 0.9, letterSpacing: '-0.055em' }}>
            Inside the DeepSentinel{' '}
            <span className="serif-i normal-case" style={{ color: 'var(--acid)' }}>Multi-Modal Forensic Engine</span>
          </h1>
          <p className="mt-6 max-w-3xl text-[1.0625rem] leading-relaxed sm:text-lg" style={{ color: '#a7e1c5' }}>
            DeepSentinel checks images, voice clips and videos for signs of AI generation or manipulation. This page opens
            the case file: how a file travels through the system, which models make the call, how they were tested,
            what failed along the way, and where the tool is still weak. Every number cites the file it comes from.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ['Media types', '3', 'Image · audio · video'],
              ['File fingerprint', 'SHA-256', 'Recorded on upload'],
              ['Borderline scores', 'Inconclusive', 'Never forced'],
              ['Heuristic checks', 'Labelled', 'No vote in the verdict'],
            ].map(([label, value, hint], i) => (
              <motion.div key={label} initial={{ opacity: 0, y: 20, rotate: i % 2 ? 2 : -2 }} animate={{ opacity: 1, y: 0, rotate: i % 2 ? 1 : -1 }}
                          transition={{ delay: 0.2 + i * 0.08, type: 'spring', stiffness: 200, damping: 16 }}
                          className="rounded-lg border-2 border-[#191919] p-3.5 text-[#191919]" style={{ background: i === 0 ? 'var(--acid)' : 'var(--mint-soft)' }}>
                <span className="mono block text-[0.625rem] font-bold uppercase tracking-wider opacity-70">{label}</span>
                <span className="wide mt-1 block text-xl font-black uppercase leading-tight">{value}</span>
                <span className="text-[0.6875rem] opacity-75">{hint}</span>
              </motion.div>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap gap-2">
            {CHAPTERS.map(([id, label], i) => (
              <a key={id} href={`#${id}`} className="mono rounded-md border-2 px-2.5 py-1 text-[0.6875rem] font-bold uppercase transition-all hover:-translate-y-0.5 hover:bg-[var(--acid)] hover:text-[#191919]"
                 style={{ borderColor: '#246a48' }}>
                {String(i + 1).padStart(2, '0')} {label}
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-12">
        <NumbersBoard />
      </section>

      <div className="bleed my-10">
        <Marquee items={['Upload', 'Fingerprint', 'Queue', 'Route', 'Score', 'Decide', 'Report']} tone="mint" tilt={-1.5} />
      </div>

      <PartDivider roman="I" title="Why" sub="The problem DeepSentinel was built to tackle, and what it set out to do." />

      <Chapter id="problem" kicker="The problem" title={<>When <span className="serif-i normal-case text-gradient">anything</span> can be faked.</>}
               intro="Generative AI makes convincing fake photos, cloned voices and face-swapped videos cheap to produce. Most existing tools answer with one unexplained number. DeepSentinel was built to do better.">
        <ProblemSection />
      </Chapter>

      <Chapter id="objectives" kicker="Objectives" title={<>Nine <span className="serif-i normal-case text-gradient">promises</span>.</>}
               intro="What the project set out to build, from the original objectives document.">
        <ObjectivesBoard />
      </Chapter>

      <PartDivider roman="II" title="How" sub="The system, layer by layer, and the path one file takes through it." />

      <Chapter id="architecture" kicker="System architecture" title={<>Five layers, <span className="serif-i normal-case text-gradient">one</span> system.</>}
               intro="Click a layer to open it. Each one only talks to the layer next to it.">
        <ArchitectureStack />
      </Chapter>

      <Chapter id="systemmap" kicker="System map" title={<>Watch the <span className="serif-i normal-case text-gradient">data</span> move.</>}
               intro="Every container and every connection in a running deployment. The dots are requests in flight; hover a box to see what it does and what it talks to.">
        <SystemMap />
      </Chapter>

      <Chapter id="journey" kicker="The journey of a file" title={<>From upload to <span className="serif-i normal-case text-gradient">report</span>.</>}
               intro="Nine stops, three lanes. Click any box to read what happens there, or let it play.">
        <JourneyFlow />
      </Chapter>

      <Chapter id="band" kicker="The verdict band" title={<>Why <span className="serif-i normal-case text-gradient">inconclusive</span> exists.</>}
               intro="A detector gives a score, not a verdict. Two cut-offs turn the score into an answer, and the gap between them is kept on purpose: near the middle, the honest answer is “we can’t tell”.">
        <BandSimulator />
      </Chapter>

      <Chapter id="decide" kicker="How a verdict is made" title={<>One clip, <span className="serif-i normal-case text-gradient">one</span> score.</>}
               intro="How an audio clip is cut into windows, scored piece by piece, and averaged into the number the verdict uses.">
        <AudioWindows />
      </Chapter>

      <Chapter id="engines" kicker="Three engines" title={<>One box, <span className="serif-i normal-case text-gradient">three</span> specialists.</>}
               intro="Each media type has its own models. Only the models below vote on the verdict; everything else on a result page is supporting context.">
        <div className="grid gap-6 lg:grid-cols-3">
          {ENGINES.map((e, i) => (
            <motion.article key={e.id} {...reveal(i * 0.08)} className="flex flex-col rounded-2xl border-2 border-[#191919]"
                            style={{ background: 'var(--surface-1)', boxShadow: `8px 8px 0 ${e.color}` }}>
              <header className="flex items-center justify-between rounded-t-[14px] border-b-2 border-[#191919] p-5" style={{ background: e.color, color: '#191919' }}>
                <span className="flex items-center gap-3">
                  <span className="grid h-11 w-11 place-items-center rounded-md border-2 border-[#191919] bg-[#191919]" style={{ color: e.color }}><e.icon size={22} /></span>
                  <Scramble as="h3" text={e.title} className="wide block text-3xl font-black uppercase leading-none" />
                </span>
                <span className="mono text-[0.625rem] font-bold uppercase">spec sheet</span>
              </header>
              <dl className="flex-1 divide-y-2 divide-[var(--border-subtle)] px-5">
                {e.rows.map(([k, v]) => (
                  <div key={k} className="py-4">
                    <dt className="mono text-[0.6875rem] font-bold uppercase text-accent">{k}</dt>
                    <dd className="mt-1 text-[0.9375rem] leading-relaxed text-ink-secondary">{v}</dd>
                  </div>
                ))}
              </dl>
              <div className="px-5 pb-5"><Source>{e.src}</Source></div>
            </motion.article>
          ))}
        </div>
      </Chapter>

      <Chapter id="pipelines" kicker="Inside the pipelines" title={<>Every <span className="serif-i normal-case text-gradient">stage</span>, named.</>}
               intro="All the analysis stages that exist in the code, per media type. Bright cards decide the verdict; the rest are shown as supporting context.">
        <PipelineModules />
      </Chapter>

      <Chapter id="api" kicker="The API" title={<>The <span className="serif-i normal-case text-gradient">switchboard</span>.</>}
               intro="Everything the website does goes through these routes. Filter the console to find one.">
        <ApiSwitchboard />
      </Chapter>

      <Chapter id="security" kicker="Security & privacy" title={<>Built to <span className="serif-i normal-case text-gradient">forget</span> safely.</>}
               intro="How sessions, files and reports are protected, and how they are deleted.">
        <SecurityGrid />
      </Chapter>

      <PartDivider roman="III" title="Proof" sub="How it was tested, what the numbers say, and what went wrong along the way." />

      <Chapter id="results" kicker="How well it works" title={<>The <span className="serif-i normal-case text-gradient">scoreboard</span>, good and bad.</>}
               intro="Measured on test data that no setting was tuned on. The red bars are as important as the green ones.">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard title="Images: AI called manipulated" src="docs/research/EVALUATION.md §5 · evaluation/E2E-02/summary.json">
            <Bar label="COCO + Synthbuster (9 generators)" value={98.4} />
            <Bar label="Newest generators (FLUX.2, GPT Image 2, …)" value={44.0} color="#ffb020" delay={0.1} note="Another 44.4 % were inconclusive." />
            <Bar label="Small 256 px thumbnails" value={38.3} color="#ff4d3d" delay={0.2} />
            <p className="rounded-md border-2 border-[#191919] p-3 text-[0.875rem] font-semibold" style={{ background: 'var(--accent-soft)' }}>
              <Check size={14} className="mr-1 inline text-accent" /> Real photos called manipulated: <strong>0</strong> on all three test sets.
            </p>
          </ChartCard>

          <ChartCard title="Video: before and after the fix" src="docs/research/EVALUATION.md §6 · evaluation/VIDEO-GEND-01/summary.json">
            <p className="mono text-[0.6875rem] font-bold uppercase text-ink-muted">Real videos wrongly flagged</p>
            <Bar label="Old rules" value={43.3} color="#ff4d3d" />
            <Bar label="Fixed rules + GenD face model" value={2.5} delay={0.1} />
            <p className="mono pt-2 text-[0.6875rem] font-bold uppercase text-ink-muted">Face swaps caught</p>
            <Bar label="Old rules" value={51.7} color="#ffb020" delay={0.2} />
            <Bar label="Fixed rules + GenD face model" value={72.5} delay={0.3} />
          </ChartCard>

          <ChartCard title="Audio: verdicts end to end" src="docs/research/EVALUATION.md §5a · evaluation/E2E-01/summary.json">
            <p className="mono text-[0.6875rem] font-bold uppercase text-ink-muted">ASVspoof 2019 LA eval (300 + 300 clips)</p>
            <Bar label="Fakes caught" value={97.7} />
            <Bar label="Real speech wrongly flagged" value={0.3} delay={0.1} />
            <p className="mono pt-2 text-[0.6875rem] font-bold uppercase text-ink-muted">ASVspoof 5 eval sample (harder, newer attacks)</p>
            <Bar label="Fakes caught" value={77.0} color="#ffb020" delay={0.2} />
            <Bar label="Real speech wrongly flagged" value={15.0} color="#ff4d3d" delay={0.3} />
          </ChartCard>

          <ChartCard title="Fallback audio model under compression" src="docs/research/EVALUATION.md §3 · results/robustness.json (audio)">
            <p className="mono text-[0.6875rem] font-bold uppercase text-ink-muted">Genuine speech correctly called authentic</p>
            <Bar label="Original FLAC" value={99.8} />
            <Bar label="Opus 32 kbit/s" value={99.6} delay={0.1} />
            <Bar label="MP3 64 kbit/s" value={0.0} color="#ff4d3d" delay={0.2} note="MP3 breaks this model: every genuine clip is called AI-generated (KNOWN_ISSUES #14)." />
          </ChartCard>
        </div>

        <div className="mt-6"><GeneratorChart /></div>

        {/* real figures, pinned like evidence prints */}
        <motion.div {...reveal()} className="mt-12 rounded-2xl border-2 border-[#191919] p-6 sm:p-10" style={{ background: 'var(--sea)' }}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="sticker" style={{ '--r': '-2deg', background: '#ececed' }}>Evidence board</span>
            <span className="mono text-[0.6875rem] font-bold uppercase text-[#a7e1c5]">The project’s own plots · click to open full size</span>
          </div>
          <div className="mt-8 grid gap-10 sm:grid-cols-2">
            {FIGURES.map(([file, caption, src, r]) => (
              <a key={file} href={`/figures/${file}`} target="_blank" rel="noreferrer"
                 className="group relative block rounded-sm bg-white p-3 pb-12 transition-transform duration-300 hover:z-10 hover:scale-[1.03]"
                 style={{ transform: `rotate(${r}deg)`, boxShadow: '8px 8px 0 #191919' }}>
                <span className="absolute -top-3 left-1/2 h-6 w-24 -translate-x-1/2 rotate-[-3deg] opacity-80" style={{ background: 'var(--acid)' }} aria-hidden="true" />
                <img src={`/figures/${file}`} alt={caption} loading="lazy" className="w-full border border-[#c2c2c5]" />
                <span className="absolute inset-x-3 bottom-2.5 text-[#191919]">
                  <span className="serif-i block text-[1.125rem] leading-tight">{caption}</span>
                  <span className="mono block truncate text-[0.5625rem] opacity-60">{src}</span>
                </span>
              </a>
            ))}
          </div>
        </motion.div>
      </Chapter>

      <Chapter id="deepdive" kicker="Charts deep-dive" title={<>Four more ways to <span className="serif-i normal-case text-gradient">read</span> the results.</>}
               intro="The same evaluation, drawn so the pattern jumps out: where the audio model breaks, what the video fix changed, how a harder test hurts, and how big the models really are.">
        <div className="space-y-8">
          <AttackRadial />
          <VideoWaffles />
          <AudioDumbbell />
          <ModelScale />
        </div>
      </Chapter>

      <Chapter id="speed" kicker="Speed" title={<>How long a scan <span className="serif-i normal-case text-gradient">takes</span>.</>}
               intro="Median time per file through the full worker pipeline on one machine: Intel Core i9-14900 and an NVIDIA RTX 5070. Image inputs here are small, so phone photos take longer.">
        <div className="grid gap-6 md:grid-cols-3">
          {[
            ['Image', ImageIcon, 0.27, 0.54],
            ['Audio', Waveform, 1.11, 1.19],
            ['Video (10 s clip)', VideoIcon, 1.77, 2.14],
          ].map(([label, Icon, gpu, cpu], i) => (
            <motion.div key={label} {...reveal(i * 0.08)} className="rounded-2xl border-2 border-[#191919] p-6" style={{ background: 'var(--surface-1)', boxShadow: '6px 6px 0 #000' }}>
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-md border-2 border-[#191919] bg-[var(--acid)] text-[#191919]"><Icon size={18} /></span>
                <h3 className="wide text-xl font-black uppercase">{label}</h3>
              </div>
              <div className="mt-5 space-y-4">
                <Bar label="GPU p50" value={gpu} max={2.5} suffix=" s" />
                <Bar label="CPU p50" value={cpu} max={2.5} suffix=" s" color="var(--teal)" delay={0.1} />
              </div>
            </motion.div>
          ))}
        </div>
        <Source>docs/research/EVALUATION.md §4 · results/latency.json. Video with GenD on and real speech takes longer: median 20.7 s per DFD video (§6).</Source>
      </Chapter>

      <Chapter dark id="rejected" kicker="Tried & rejected" title={<>What we got <span className="serif-i normal-case" style={{ color: 'var(--acid)' }}>wrong</span>, and fixed.</>}
               intro="A detector is only as honest as its record of mistakes. These are the changes that mattered most, each decided by a rule written down before the test was run.">
        <ol className="relative space-y-6 border-l-4 pl-6 sm:pl-10" style={{ borderColor: 'var(--sea)' }}>
          {LOG.map((e, i) => (
            <motion.li key={e.title} {...reveal(i * 0.05)} className="relative">
              <span className="absolute -left-[2.15rem] top-6 h-5 w-5 rounded-full border-4 sm:-left-[3.15rem]" style={{ borderColor: '#191919', background: e.color }} aria-hidden="true" />
              <div className="relative rounded-xl border-2 border-[#191919] p-5 pr-28 text-[#191919] sm:p-6 sm:pr-36" style={{ background: '#ececed', boxShadow: '6px 6px 0 #191919' }}>
                <span className="mono absolute right-4 top-4 rotate-[8deg] rounded-md border-[3px] px-2 py-0.5 text-[0.75rem] font-bold uppercase sm:text-sm"
                      style={{ borderColor: e.color === 'var(--acid)' ? '#036727' : e.color, color: e.color === 'var(--acid)' ? '#036727' : e.color }}>
                  {e.stamp}
                </span>
                <h3 className="wide text-xl font-black uppercase leading-tight tracking-tight sm:text-2xl">{e.title}</h3>
                <p className="mt-2 text-[0.9375rem] leading-relaxed">{e.body}</p>
                <p className="mono mt-3 text-[0.625rem] opacity-60">SRC {e.src}</p>
              </div>
            </motion.li>
          ))}
        </ol>
      </Chapter>

      <Chapter id="timeline" kicker="Timeline" title={<>How it <span className="serif-i normal-case text-gradient">got here</span>.</>}
               intro="The milestones that shaped the current system, with the dates they landed.">
        <Timeline />
      </Chapter>

      <Chapter id="data" kicker="Datasets" title={<>What it <span className="serif-i normal-case text-gradient">learned</span> and was tested on.</>}
               intro="Training data and test data are kept apart, and every threshold is chosen on a development split before the test split is scored once.">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {DATASETS.map(([name, role, lic], i) => (
            <motion.div key={name} {...reveal(i * 0.04)}
                        className="group rounded-xl border-2 border-[#191919] p-5 transition-all hover:-translate-x-1 hover:-translate-y-1"
                        style={{ background: i % 3 === 0 ? 'var(--acid)' : i % 3 === 1 ? 'var(--mint-soft)' : 'var(--teal)', color: '#191919', boxShadow: '5px 5px 0 #000' }}>
              <span className="mono text-[0.625rem] font-bold uppercase opacity-70">Dataset {String(i + 1).padStart(2, '0')}</span>
              <h3 className="wide mt-1 text-lg font-black uppercase leading-tight">{name}</h3>
              <p className="mt-2 text-[0.9375rem] font-medium">{role}</p>
              <p className="mono mt-3 text-[0.625rem] opacity-70">{lic}</p>
            </motion.div>
          ))}
        </div>
        <Source>docs/research/DATASETS.md · full licences in docs/paper_upgrade/DATA_STATEMENT.md</Source>
        <div className="mt-8"><DevTestFlow /></div>
      </Chapter>

      <Chapter id="limits" kicker="Known limits" title={<>Where it can be <span className="serif-i normal-case" style={{ color: '#ff4d3d' }}>wrong</span>.</>}
               intro="Read these before trusting any single result.">
        <div className="grid gap-4 md:grid-cols-2">
          {LIMITS.map(([title, body, ref], i) => (
            <motion.div key={title} {...reveal(i * 0.04)} className="flex gap-4 rounded-xl border-2 p-5"
                        style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-1)' }}>
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md border-2 border-[#191919]" style={{ background: '#ff4d3d', color: '#191919' }}>
                <AlertTriangle size={18} />
              </span>
              <div>
                <h3 className="font-bold text-ink-primary">{title}</h3>
                <p className="mt-1 text-[0.9375rem] leading-relaxed text-ink-secondary">{body}</p>
                <span className="mono mt-2 inline-block text-[0.625rem] font-bold text-ink-muted">KNOWN_ISSUES {ref}</span>
              </div>
            </motion.div>
          ))}
        </div>
        <motion.div {...reveal()} className="mt-6 flex items-start gap-3 rounded-xl border-2 border-[#191919] p-5 text-[#191919]" style={{ background: '#ffb020' }}>
          <X size={20} className="mt-0.5 shrink-0" />
          <p className="font-semibold">Automated assessment only. Not forensic or legal evidence. A result is a lead to check, not proof.</p>
        </motion.div>
      </Chapter>

      <PartDivider roman="IV" title="Build" sub="How it is deployed, tested and put together, plus a glossary of the terms used here." />

      <Chapter id="explorer" kicker="Project explorer" title={<>Open the <span className="serif-i normal-case text-gradient">box</span>.</>}
               intro="What lives where in the repository. Pick a folder on the left.">
        <ProjectExplorer />
      </Chapter>

      <Chapter id="deploy" kicker="Deployment" title={<>Six <span className="serif-i normal-case text-gradient">containers</span>.</>}
               intro="The production setup runs as six Docker services. Only the worker loads the models.">
        <DeployMap />
      </Chapter>

      <Chapter id="testing" kicker="Testing & reproducibility" title={<>Checked, then <span className="serif-i normal-case text-gradient">re-checked</span>.</>}
               intro="Four layers of checks, from unit tests to rebuilding every published number from raw scores.">
        <TestingBoard />
      </Chapter>

      <Chapter id="glossary" kicker="Glossary" title={<>Words, <span className="serif-i normal-case text-gradient">decoded</span>.</>}
               intro="The terms used on this page. Tap a card to flip it.">
        <Glossary />
      </Chapter>

      <Chapter id="faq" kicker="FAQ" title={<>Straight <span className="serif-i normal-case text-gradient">answers</span>.</>}
               intro="The questions people ask most, answered without spin.">
        <Faq />
      </Chapter>

      <Chapter id="stack" kicker="Under the hood" title={<>The <span className="serif-i normal-case text-gradient">machine</span> room.</>}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STACK.map(([k, v, Icon], i) => (
            <motion.div key={k} {...reveal(i * 0.04)} className="card card-hover flex items-start gap-4 p-5">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md border-2 border-[#191919] bg-[var(--acid)] text-[#191919]"><Icon size={18} /></span>
              <div>
                <p className="mono text-[0.6875rem] font-bold uppercase text-accent">{k}</p>
                <p className="mt-1 font-semibold text-ink-primary">{v}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div {...reveal()} className="mt-12 flex flex-col items-start justify-between gap-6 rounded-2xl border-2 border-[#191919] p-8 sm:flex-row sm:items-center"
                    style={{ background: 'var(--acid)', color: '#191919', boxShadow: '10px 10px 0 var(--pop)' }}>
          <h3 className="wide font-black uppercase" style={{ fontSize: 'clamp(1.75rem, 3.5vw, 3rem)', lineHeight: 0.92, letterSpacing: '-0.05em' }}>
            Seen enough?<br /><span className="serif-i normal-case">Try it on a file.</span>
          </h3>
          <Link to="/analyse" className="btn btn-lg group border-[#191919] bg-[#191919] uppercase text-[var(--acid)] shadow-[6px_6px_0_#ececed] hover:-translate-x-1 hover:-translate-y-1"
                style={{ fontStretch: '115%', fontWeight: 800 }}>
            Analyse a file <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </motion.div>
      </Chapter>
    </div>
  )
}
