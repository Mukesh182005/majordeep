import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertTriangle, Check, Clock, Cpu, Database, Eye, FileText, GitBranch, Globe, Hash,
  Image as ImageIcon, Lock, Network, Search, Shield, Video as VideoIcon, Waveform, X,
} from '../ui/Icons'

// Extra chapters for the How it works page. Facts are taken from the code and
// the project's docs; each block names where it comes from.
//   docs/college/PROBLEM_STATEMENT.md, docs/college/OBJECTIVES.md,
//   docs/architecture/SYSTEM_ARCHITECTURE.md, docs/SECURITY.md,
//   backend/app/routers/*, backend/app/models.py, backend/app/ml/**,
//   docker-compose.yml, KNOWN_ISSUES.md (Resolved), docs/research/EVALUATION.md

const ease = [0.2, 0.9, 0.3, 1]
const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.6, delay, ease },
})

export function Src({ children, light = false }) {
  return (
    <p className={`mono mt-3 text-[0.6875rem] leading-relaxed ${light ? 'text-[#a7e1c5]' : 'text-ink-muted'}`}>
      <span className={`mr-1 font-bold ${light ? 'text-[var(--acid)]' : 'text-accent'}`}>SRC</span>{children}
    </p>
  )
}

/** Big divider that opens each of the four parts of the page. */
export function PartDivider({ roman, title, sub }) {
  return (
    <motion.div {...reveal()} className="bleed relative my-10 overflow-hidden border-y-2 border-[#191919] py-10 sm:py-14"
                style={{ background: 'var(--acid)', color: '#191919' }}>
      <div className="pointer-events-none absolute inset-0 opacity-25"
           style={{ backgroundImage: 'radial-gradient(#191919 1.2px, transparent 1.2px)', backgroundSize: '18px 18px' }} aria-hidden="true" />
      <div className="relative mx-auto flex max-w-content flex-wrap items-end justify-between gap-4 px-4 sm:px-6 lg:px-10">
        <div className="flex items-end gap-5">
          <span className="serif-i leading-none" style={{ fontSize: 'clamp(4rem, 10vw, 9rem)' }}>{roman}</span>
          <div className="pb-2">
            <span className="mono text-[0.75rem] font-bold uppercase">Part {roman}</span>
            <h2 className="wide font-black uppercase leading-none" style={{ fontSize: 'clamp(2rem, 5vw, 4.5rem)', letterSpacing: '-0.05em' }}>{title}</h2>
          </div>
        </div>
        <p className="max-w-sm pb-2 text-[1rem] font-semibold">{sub}</p>
      </div>
    </motion.div>
  )
}

// ─── The problem ────────────────────────────────────────────────────────────

const THREATS = [
  ['Misinformation', 'Fabricated photos and videos are used to spread false stories.', Globe],
  ['Identity fraud', 'Voice clones and face swaps make impersonation cheap.', Shield],
  ['Evidence tampering', 'Edited media can undermine journalistic and legal records.', FileText],
  ['Erosion of trust', 'When anything could be fake, even real media gets doubted.', Eye],
]

const GAPS = [
  ['Image only', 'Three media types, each with its own detectors'],
  ['One opaque score', 'A verdict plus the evidence behind it'],
  ['Forced real / fake', 'An explicit INCONCLUSIVE band'],
  ['Nothing kept', 'SHA-256 fingerprint, stored result and PDF report'],
  ['Neural score only', 'Signal-level checks shown alongside, clearly labelled'],
]

export function ProblemSection() {
  return (
    <div className="space-y-10">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {THREATS.map(([t, b, Icon], i) => (
          <motion.div key={t} {...reveal(i * 0.06)} className="relative overflow-hidden rounded-xl border-2 border-[#191919] p-5"
                      style={{ background: 'var(--surface-1)', boxShadow: '5px 5px 0 #ff4d3d' }}>
            <span className="wide pointer-events-none absolute -right-2 -top-4 text-[5rem] font-black leading-none text-outline" aria-hidden="true">{i + 1}</span>
            <span className="grid h-10 w-10 place-items-center rounded-md border-2 border-[#191919] bg-[#ff4d3d] text-[#191919]"><Icon size={18} /></span>
            <h3 className="wide mt-4 text-lg font-black uppercase">{t}</h3>
            <p className="mt-1.5 text-[0.9375rem] text-ink-secondary">{b}</p>
          </motion.div>
        ))}
      </div>

      {/* split-screen comparison */}
      <motion.div {...reveal()} className="overflow-hidden rounded-2xl border-2 border-[#191919]" style={{ boxShadow: '10px 10px 0 var(--acid)' }}>
        <div className="grid grid-cols-2 border-b-2 border-[#191919]">
          <div className="p-4 sm:p-6" style={{ background: '#28282b' }}>
            <span className="mono text-[0.6875rem] font-bold uppercase text-[#8a8a92]">Most detectors</span>
          </div>
          <div className="p-4 sm:p-6" style={{ background: 'var(--acid)', color: '#191919' }}>
            <span className="mono text-[0.6875rem] font-bold uppercase">DeepSentinel</span>
          </div>
        </div>
        {GAPS.map(([before, after], i) => (
          <motion.div key={before} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                      className="grid grid-cols-2 border-b-2 border-[#191919] last:border-b-0">
            <div className="flex items-center gap-3 p-4 sm:p-5" style={{ background: '#222224', color: '#8a8a92' }}>
              <X size={16} className="shrink-0 text-[#ff4d3d]" />
              <span className="text-[0.9375rem] line-through decoration-[#ff4d3d] decoration-2">{before}</span>
            </div>
            <div className="flex items-center gap-3 p-4 sm:p-5" style={{ background: '#ececed', color: '#191919' }}>
              <Check size={16} className="shrink-0 text-[#036727]" />
              <span className="text-[0.9375rem] font-semibold">{after}</span>
            </div>
          </motion.div>
        ))}
      </motion.div>
      <Src>docs/college/PROBLEM_STATEMENT.md</Src>
    </div>
  )
}

const OBJECTIVES = [
  'Detect AI-generated and manipulated images, audio and video',
  'Combine neural detectors with signal-level forensic checks',
  'Give explainable evidence, not just a score',
  'Report uncertainty with an INCONCLUSIVE verdict',
  'Fingerprint every upload and report with SHA-256',
  'Generate a PDF report with results, evidence and limits',
  'Ship as a full web app: React, FastAPI, Celery, Postgres, Docker',
  'Validate uploads, rate-limit, trace requests, enforce safe config',
  'Document limitations honestly instead of overclaiming',
]

export function ObjectivesBoard() {
  return (
    <div>
      <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {OBJECTIVES.map((o, i) => (
          <motion.li key={o} {...reveal(i * 0.04)}
                     className="group flex items-start gap-3 rounded-xl border-2 border-[#191919] p-4 transition-transform hover:-rotate-1"
                     style={{ background: i % 2 ? 'var(--mint-soft)' : '#ececed', color: '#191919', boxShadow: '4px 4px 0 #000' }}>
            <span className="wide grid h-9 w-9 shrink-0 place-items-center rounded-md border-2 border-[#191919] bg-[#191919] text-sm font-black text-[var(--acid)]">
              {String(i + 1).padStart(2, '0')}
            </span>
            <span className="pt-1 text-[0.9375rem] font-semibold leading-snug">{o}</span>
          </motion.li>
        ))}
      </ol>
      <Src>docs/college/OBJECTIVES.md</Src>
    </div>
  )
}

// ─── Architecture stack ─────────────────────────────────────────────────────

const LAYERS = [
  { name: 'Presentation', tech: 'React 18 · Vite · Tailwind · Framer Motion', color: 'var(--acid)', icon: Globe,
    items: ['Pages: Landing, Analyse, Result, Report, History, How it works, Privacy, Sign in', 'Per-media result views: image, audio and video forensics', 'Live job progress over a WebSocket', 'httpOnly cookie session; no token in browser storage'] },
  { name: 'Application', tech: 'FastAPI · Pydantic · SQLAlchemy · Alembic', color: 'var(--mint-soft)', icon: Network,
    items: ['Routers: auth, upload, jobs, history, health, report verification', 'Middleware: CORS, security headers, request IDs, rate limits', 'Oversized uploads rejected before the body is read', 'Refuses to start in production with a weak secret, debug on, or a wildcard CORS origin'] },
  { name: 'Queue', tech: 'Celery · Redis · Celery beat', color: 'var(--teal)', icon: Clock,
    items: ['One analysis task per upload, run by a worker', 'Without Redis, jobs run inline (handy for development)', 'A scheduled beat task deletes guest jobs after the retention window'] },
  { name: 'Inference', tech: 'PyTorch · Hugging Face · OpenCV', color: 'var(--mint)', icon: Cpu,
    items: ['Image, audio and video pipelines', 'Verdict rules with an uncertainty band', 'Checkpoints checked by SHA-256 before loading', 'PDF report generator (ReportLab, Matplotlib)'] },
  { name: 'Persistence', tech: 'PostgreSQL · file storage', color: '#ececed', icon: Database,
    items: ['Tables: users, jobs, reports, upload_events', 'Evidence stored as JSON on each job', 'Folders: uploads, evidence images, PDF reports', 'Model weights in checkpoints/'] },
]

export function ArchitectureStack() {
  const [open, setOpen] = useState(0)
  return (
    <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr] lg:items-center">
      {/* stacked slabs */}
      <div className="relative mx-auto w-full max-w-xl py-4" style={{ perspective: '1200px' }}>
        {LAYERS.map((l, i) => (
          <motion.button key={l.name} onClick={() => setOpen(i)} aria-pressed={open === i}
            initial={{ opacity: 0, y: -40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            transition={{ delay: i * 0.1, type: 'spring', stiffness: 200, damping: 18 }}
            className="relative -mt-3 block w-full rounded-xl border-2 border-[#191919] p-4 text-left text-[#191919] transition-all duration-300 first:mt-0 sm:p-5"
            style={{
              background: l.color, zIndex: LAYERS.length - i,
              transform: `translateX(${open === i ? 0 : i * 10}px) rotateX(${open === i ? 0 : 8}deg)`,
              boxShadow: open === i ? '10px 10px 0 var(--pop)' : '4px 4px 0 #191919',
              marginLeft: open === i ? '-12px' : 0,
            }}>
            <span className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-md border-2 border-[#191919] bg-[#191919]" style={{ color: l.color }}><l.icon size={17} /></span>
                <span className="wide text-lg font-black uppercase leading-none sm:text-xl">{l.name}</span>
              </span>
              <span className="mono hidden text-[0.625rem] font-bold uppercase sm:block">Layer {i + 1}</span>
            </span>
          </motion.button>
        ))}
      </div>

      <motion.div key={open} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, ease }}
                  className="rounded-2xl border-2 p-6 sm:p-8" style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-1)' }}>
        <span className="mono text-[0.6875rem] font-bold uppercase text-accent">Layer {open + 1} of {LAYERS.length}</span>
        <h3 className="wide mt-2 text-3xl font-black uppercase leading-none">{LAYERS[open].name}</h3>
        <p className="mono mt-2 text-[0.8125rem] text-ink-secondary">{LAYERS[open].tech}</p>
        <ul className="mt-5 space-y-2.5">
          {LAYERS[open].items.map((it) => (
            <li key={it} className="flex gap-3 text-[0.9375rem] text-ink-primary">
              <span className="mt-2 h-2 w-2 shrink-0" style={{ background: 'var(--acid)' }} />{it}
            </li>
          ))}
        </ul>
        <Src>docs/architecture/SYSTEM_ARCHITECTURE.md · docs/SECURITY.md · backend/app</Src>
      </motion.div>
    </div>
  )
}

// ─── Pipeline modules ───────────────────────────────────────────────────────
// vote: true = part of the verdict. Everything else is shown as context; the
// evaluation found no non-model stage that separates real from fake.

const MODULES = {
  image: [
    ['Scene AI ensemble (SwinV2 + Community Forensics ViT ×2)', true],
    ['Metadata & C2PA provenance', true],
    ['Screenshot / letterbox border crop', true],
    ['TruFor edit-region heatmap', false],
    ['Camera CFA demosaicing check', false],
    ['Tampering & splicing localisation', false],
    ['Steganography scan', false],
    ['Invisible watermark scan', false],
    ['Screen recapture check', false],
    ['File security & container check', false],
    ['Grad-CAM attention heatmap', false],
    ['Out-of-distribution guard', false],
    ['Face-crop model (StyleGAN-trained)', false],
  ],
  audio: [
    ['pellav2 anti-spoofing model (w2v-BERT 2.0)', true],
    ['LCNN on LFCC (fallback when pellav2 cannot run)', true],
    ['Per-window score timeline', true],
    ['Codec guard', false],
    ['Signal intelligence descriptors', false],
    ['Glottal flow & voice quality', false],
    ['Mains-hum (ENF) analysis', false],
    ['Splice timeline', false],
    ['File container DNA', false],
    ['Watermark & provenance checks', false],
  ],
  video: [
    ['Container & bitstream forensics', false],
    ['Scene & shot boundary segmentation', false],
    ['Scene AI detectors on sampled frames', true],
    ['GenD face-swap model (mean over face frames)', true],
    ['Temporal jitter & facial dynamics', false],
    ['Remote photoplethysmography (rPPG)', false],
    ['Spatio-temporal tensor dynamics', false],
    ['LipForensics articulatory kinematics', false],
    ['Optical flow motion decomposition', false],
    ['Acoustic speech & cross-modal lip sync', false],
    ['AI generator attribution', false],
  ],
}

const MOD_META = {
  image: { label: 'Image', icon: ImageIcon, color: 'var(--acid)' },
  audio: { label: 'Audio', icon: Waveform, color: 'var(--teal)' },
  video: { label: 'Video', icon: VideoIcon, color: 'var(--mint)' },
}

export function PipelineModules() {
  const [tab, setTab] = useState('image')
  const [onlyVotes, setOnlyVotes] = useState(false)
  const list = MODULES[tab].filter(([, v]) => !onlyVotes || v)
  const votes = MODULES[tab].filter(([, v]) => v).length
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-2" role="tablist">
          {Object.entries(MOD_META).map(([k, m]) => (
            <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                    className="wide flex items-center gap-2 rounded-md border-2 px-4 py-2 text-[0.9375rem] font-black uppercase transition-all"
                    style={{ borderColor: tab === k ? '#191919' : 'var(--border-strong)', background: tab === k ? m.color : 'var(--surface-1)', color: tab === k ? '#191919' : undefined, boxShadow: tab === k ? '4px 4px 0 var(--pop)' : 'none' }}>
              <m.icon size={16} />{m.label}
            </button>
          ))}
        </div>
        <label className="mono flex cursor-pointer items-center gap-2 text-[0.75rem] font-bold uppercase">
          <input type="checkbox" checked={onlyVotes} onChange={(e) => setOnlyVotes(e.target.checked)} className="h-4 w-4 accent-[var(--acid)]" />
          Only what votes
        </label>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {list.map(([name, vote], i) => (
          <motion.div key={tab + name} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.03 }}
                      className="flex items-start justify-between gap-3 rounded-lg border-2 p-4"
                      style={{ borderColor: vote ? '#191919' : 'var(--border-strong)', background: vote ? MOD_META[tab].color : 'var(--surface-1)', color: vote ? '#191919' : undefined, boxShadow: vote ? '4px 4px 0 #000' : 'none' }}>
            <span className="text-[0.9375rem] font-semibold leading-snug">{name}</span>
            <span className="mono shrink-0 rounded-sm border-2 px-1.5 py-0.5 text-[0.5625rem] font-bold uppercase"
                  style={{ borderColor: vote ? '#191919' : 'var(--border-strong)', background: vote ? '#191919' : 'transparent', color: vote ? 'var(--acid)' : 'var(--text-muted)' }}>
              {vote ? 'Votes' : 'Shown only'}
            </span>
          </motion.div>
        ))}
      </div>
      <p className="mt-5 text-[0.9375rem] text-ink-secondary">
        <strong className="text-ink-primary">{votes} of {MODULES[tab].length}</strong> {MOD_META[tab].label.toLowerCase()} stages decide the verdict.
        The rest appear on the result page as context, marked unvalidated: in testing, no stage other than the models separated real from fake.
      </p>
      <Src>backend/app/ml/{'{forensics,audio,video}'} · docs/research/EVALUATION.md §5, §5a, §6 (stage diagnosis) · KNOWN_ISSUES #19</Src>
    </div>
  )
}

// ─── API switchboard ────────────────────────────────────────────────────────

const ENDPOINTS = [
  ['GET', '/api/health', 'Is the service up, and which models are loaded'],
  ['POST', '/api/auth/register', 'Create an account'],
  ['POST', '/api/auth/login', 'Sign in; sets an httpOnly session cookie'],
  ['POST', '/api/auth/logout', 'Clear the session cookie'],
  ['GET', '/api/auth/me', 'The signed-in user'],
  ['GET', '/api/upload/limits', 'Size, types, durations and rate limits'],
  ['POST', '/api/upload', 'Send a file; returns a job id'],
  ['GET', '/api/jobs/{id}/status', 'Queued, running, done or failed'],
  ['WS', '/api/jobs/{id}/ws', 'Live progress stream'],
  ['GET', '/api/jobs/{id}/result', 'Verdict, scores and evidence'],
  ['GET', '/api/jobs/{id}/evidence/{kind}', 'Heatmaps and other evidence images'],
  ['POST', '/api/jobs/{id}/links', 'Short-lived signed links for report and stream'],
  ['POST', '/api/jobs/{id}/report', 'Build the PDF report'],
  ['GET', '/api/jobs/{id}/report', 'Download the PDF'],
  ['GET', '/api/reports/{ref}/verify', 'Check a report’s hash'],
  ['GET', '/api/history', 'Your past scans'],
  ['DELETE', '/api/history/{id}', 'Delete a scan and all its files'],
]

const METHOD_COLOR = { GET: 'var(--acid)', POST: '#ffb020', DELETE: '#ff4d3d', WS: 'var(--teal)' }

export function ApiSwitchboard() {
  const [q, setQ] = useState('')
  const shown = ENDPOINTS.filter((e) => (e.join(' ').toLowerCase()).includes(q.toLowerCase()))
  return (
    <motion.div {...reveal()} className="overflow-hidden rounded-2xl border-2 border-[#191919]" style={{ background: '#191919', boxShadow: '10px 10px 0 var(--acid)' }}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-[#333337] px-4 py-3" style={{ background: '#28282b' }}>
        <span className="mono flex items-center gap-2 text-[0.75rem] font-bold uppercase text-[#a7a7ab]">
          <span className="h-2.5 w-2.5 rounded-full bg-[#ff4d3d]" /><span className="h-2.5 w-2.5 rounded-full bg-[#ffb020]" /><span className="h-2.5 w-2.5 rounded-full bg-[var(--acid)]" />
          &nbsp;api://deepsentinel · {ENDPOINTS.length} routes
        </span>
        <label className="flex items-center gap-2 rounded-md border-2 border-[#444449] px-2 py-1">
          <Search size={14} className="text-[#8a8a92]" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="filter: report, auth, ws…" aria-label="Filter endpoints"
                 className="mono w-44 bg-transparent text-[0.75rem] text-[#ececed] outline-none placeholder:text-[#56565c]" />
        </label>
      </div>
      <ul className="mono max-h-[28rem] divide-y divide-[#28282b] overflow-y-auto text-[0.8125rem]">
        {shown.map(([m, path, desc]) => (
          <li key={m + path} className="group grid grid-cols-[4.5rem_1fr] gap-x-3 px-4 py-2.5 transition-colors hover:bg-[#222224] sm:grid-cols-[4.5rem_minmax(0,22rem)_1fr]">
            <span className="font-bold" style={{ color: METHOD_COLOR[m] }}>{m}</span>
            <span className="truncate text-[#ececed]">{path}</span>
            <span className="col-span-2 text-[#8a8a92] group-hover:text-[#a7e1c5] sm:col-span-1">{desc}</span>
          </li>
        ))}
        {!shown.length && <li className="px-4 py-6 text-[#8a8a92]">No route matches “{q}”.</li>}
      </ul>
      <div className="px-4 pb-4"><Src light>backend/app/routers/* · interactive docs at /docs when the API runs</Src></div>
    </motion.div>
  )
}

// ─── Security & privacy ─────────────────────────────────────────────────────

const SECURITY = [
  [Lock, 'Cookie sessions', 'Sign-in sets an httpOnly, SameSite=Lax cookie. No token is kept in browser storage.'],
  [Clock, '5-minute signed links', 'Report downloads and the live stream use HMAC-signed links that expire after five minutes.'],
  [Shield, 'Safe-start checks', 'In production the API refuses to start with a weak secret, debug mode or a wildcard CORS origin.'],
  [Hash, 'Fingerprints', 'Every upload and every report is SHA-256 hashed; a verify endpoint checks a report against its hash.'],
  [AlertTriangle, 'Upload limits', 'Type, size and duration checks, with per-user and per-IP rate limits a client can’t spoof.'],
  [Database, 'Your data only', 'Users see only their own history. Deleting a scan removes the upload, every evidence file and the report.'],
  [Clock, 'Guest retention', 'A scheduled task deletes guest scans after the retention window.'],
  [Network, 'Traceable requests', 'Every request gets an ID; errors return the ID, never a stack trace.'],
]

export function SecurityGrid() {
  return (
    <div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SECURITY.map(([Icon, t, b], i) => (
          <motion.div key={t} {...reveal(i * 0.04)} className="group relative overflow-hidden rounded-xl border-2 p-5 transition-colors duration-300 hover:border-[#191919] hover:bg-[var(--acid)] hover:text-[#191919]"
                      style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-1)' }}>
            <span className="grid h-10 w-10 place-items-center rounded-md border-2 border-[#191919] bg-[var(--acid)] text-[#191919] transition-colors group-hover:bg-[#191919] group-hover:text-[var(--acid)]"><Icon size={18} /></span>
            <h3 className="wide mt-4 text-[1.0625rem] font-black uppercase leading-tight">{t}</h3>
            <p className="mt-1.5 text-[0.875rem] leading-relaxed opacity-80">{b}</p>
          </motion.div>
        ))}
      </div>
      <Src>docs/SECURITY.md · backend/app/routers/auth.py · backend/app/signing.py · backend/app/retention.py · backend/app/deps.py</Src>
    </div>
  )
}

// ─── Project timeline ───────────────────────────────────────────────────────

const MILESTONES = [
  ['2026-09-03', 'First commit', 'Full-stack platform set up: React frontend, FastAPI backend, image / audio / video pipelines.', 'var(--mint-soft)'],
  ['2026-10-05', 'Image verdicts rebuilt', 'A below-chance image detector replaced; log-odds fusion; screenshots handled; NaN crashes fixed; training-data leakage removed.', 'var(--acid)'],
  ['2026-10-22', 'Honest outputs', 'Models that never ran and standards claims removed from the API, PDF and UI. Audio model trained on sine waves retired.', '#ffb020'],
  ['2026-10-22', 'Real audio model', 'LCNN trained on ASVspoof 2019 LA with official protocols; evaluated once on unseen attacks.', 'var(--teal)'],
  ['2026-10-29', 'Cookie sessions', 'Tokens moved out of the browser into an httpOnly cookie; signed 5-minute links for downloads and live status.', 'var(--mint)'],
  ['2026-10-29', 'Newer generators', 'Community Forensics (plus a copy fine-tuned on FLUX.2, GPT Image 2, Nano Banana 2) joins the image verdict.', 'var(--acid)'],
  ['2026-10-29', 'Face-swap model', 'GenD scores video faces: face AUC 0.941 on 400 DFD videos, against 0.533 for the old checkpoint.', 'var(--teal)'],
]

export function Timeline() {
  return (
    <div>
      <div className="relative overflow-x-auto pb-6">
        <div className="relative flex min-w-max gap-5 pt-10">
          <div className="absolute left-0 right-0 top-[3.1rem] h-1" style={{ background: 'var(--border-strong)' }} aria-hidden="true" />
          {MILESTONES.map(([d, t, b, c], i) => (
            <motion.div key={t} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08, ease }}
                        className="relative w-64 shrink-0">
              <span className="mono absolute -top-8 left-0 text-[0.75rem] font-bold text-accent">{d}</span>
              <span className="relative z-10 mb-4 block h-5 w-5 rounded-full border-4 border-[#191919]" style={{ background: c }} />
              <div className="rounded-xl border-2 border-[#191919] p-4 text-[#191919]" style={{ background: c, boxShadow: '5px 5px 0 #000', transform: `rotate(${i % 2 ? 1 : -1}deg)` }}>
                <h3 className="wide text-lg font-black uppercase leading-tight">{t}</h3>
                <p className="mt-2 text-[0.875rem] leading-relaxed">{b}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
      <p className="mono text-[0.6875rem] text-ink-muted">← scroll sideways →</p>
      <Src>git history · KNOWN_ISSUES.md (Resolved issues, with dates)</Src>
    </div>
  )
}

// ─── Deployment map ─────────────────────────────────────────────────────────

const SERVICES = [
  ['frontend', 'nginx serving the React build; proxies /api', Globe, 'var(--acid)'],
  ['api', 'FastAPI app; no models loaded here', Network, 'var(--mint-soft)'],
  ['worker', 'Celery worker that holds the models and runs analyses', Cpu, 'var(--teal)'],
  ['beat', 'Scheduler that deletes expired guest scans', Clock, 'var(--mint)'],
  ['redis', 'Job queue between api and worker', GitBranch, '#ececed'],
  ['db', 'PostgreSQL: users, jobs, reports, upload events', Database, '#ececed'],
]

export function DeployMap() {
  return (
    <div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SERVICES.map(([name, role, Icon, c], i) => (
          <motion.div key={name} initial={{ opacity: 0, scale: 0.85, rotate: i % 2 ? 3 : -3 }} whileInView={{ opacity: 1, scale: 1, rotate: 0 }}
                      viewport={{ once: true }} transition={{ delay: i * 0.06, type: 'spring', stiffness: 220, damping: 16 }}
                      className="relative rounded-xl border-2 border-[#191919] p-5 text-[#191919]" style={{ background: c, boxShadow: '6px 6px 0 #000' }}>
            <span className="mono absolute right-3 top-3 rounded-sm bg-[#191919] px-1.5 py-0.5 text-[0.5625rem] font-bold uppercase text-[var(--acid)]">container</span>
            <Icon size={22} />
            <h3 className="mono mt-3 text-xl font-bold">{name}</h3>
            <p className="mt-1 text-[0.875rem] font-medium">{role}</p>
          </motion.div>
        ))}
      </div>
      <p className="mt-5 text-[0.9375rem] text-ink-secondary">
        One command, <code className="mono rounded-sm bg-[var(--surface-2)] px-1.5 py-0.5 text-ink-primary">docker compose up --build</code>, starts all six.
        Named volumes keep the database, queue, uploaded media and the Hugging Face model cache between restarts.
      </p>
      <Src>docker-compose.yml · docs/setup/DOCKER.md</Src>
    </div>
  )
}

// ─── Testing & reproducibility ──────────────────────────────────────────────

const TESTS = [
  ['Backend', 'pytest', 'API, pipelines, security, retention, signed links, audio regression', 'cd backend && python -m pytest -q'],
  ['Frontend', 'Vitest + Testing Library', 'Pages and forensic views render real API responses', 'cd frontend && npm test -- --run'],
  ['Browser', 'Playwright', 'Pages load cleanly, sign-in/out, uploads, no unbacked claims, no sideways scroll on phones', 'cd frontend && npm run e2e'],
  ['Results', 'regenerate_results.py', 'Rebuilds every file in results/ from per-item scores and checks they match', 'python scripts/regenerate_results.py --check'],
]

export function TestingBoard() {
  return (
    <div>
      <div className="grid gap-4 md:grid-cols-2">
        {TESTS.map(([k, tool, what, cmd], i) => (
          <motion.div key={k} {...reveal(i * 0.05)} className="overflow-hidden rounded-xl border-2 border-[#191919]" style={{ boxShadow: '5px 5px 0 #000' }}>
            <div className="flex items-center justify-between p-4 text-[#191919]" style={{ background: i % 2 ? 'var(--teal)' : 'var(--acid)' }}>
              <h3 className="wide text-lg font-black uppercase">{k}</h3>
              <span className="mono text-[0.6875rem] font-bold">{tool}</span>
            </div>
            <div className="p-4" style={{ background: 'var(--surface-1)' }}>
              <p className="text-[0.9375rem] text-ink-secondary">{what}</p>
              <code className="mono mt-3 block overflow-x-auto whitespace-nowrap rounded-md bg-[#191919] px-3 py-2 text-[0.75rem] text-[var(--acid)]">$ {cmd}</code>
            </div>
          </motion.div>
        ))}
      </div>
      <Src>README.md · Testing · docs/research/EVALUATION.md (intro)</Src>
    </div>
  )
}

// ─── Glossary flip cards ────────────────────────────────────────────────────

const GLOSSARY = [
  ['EER', 'Equal error rate', 'The point where false alarms and misses are equally likely. Lower is better.'],
  ['AUC', 'Area under the ROC curve', '1.0 = real and fake always ranked apart; 0.5 = a coin toss.'],
  ['t-DCF', 'Tandem detection cost', 'ASVspoof’s cost measure for anti-spoofing in front of a speaker-verification system. Lower is better.'],
  ['Inconclusive', 'The honest middle', 'The score sits between the two cut-offs, so no call is made.'],
  ['SHA-256', 'File fingerprint', 'A 256-bit hash. Change one byte and about half the bits flip.'],
  ['C2PA', 'Content Credentials', 'Signed provenance metadata some cameras and apps attach. Screenshots usually strip it.'],
  ['Log-odds fusion', 'Combining models', 'Each model’s probability becomes log-odds, weighted and averaged, then turned back into one probability.'],
  ['Face swap', 'Swapped identity', 'One person’s face replaced with another’s in a real video.'],
  ['ENF', 'Mains hum', 'The 50/60 Hz electrical hum some recordings pick up. Shown as context only.'],
  ['Calibration', 'Scores you can read', 'Adjusting raw outputs so a 0.8 means roughly what it says.'],
  ['Held-out test', 'Data kept aside', 'Data no setting was tuned on, scored once at the end.'],
  ['TruFor', 'Edit localiser', 'A model that highlights regions that may have been edited. Shown, not in the verdict.'],
]

function FlipCard({ term, full, body, i }) {
  const [flipped, setFlipped] = useState(false)
  return (
    <motion.button {...reveal(i * 0.03)} onClick={() => setFlipped((f) => !f)} aria-pressed={flipped}
                   className="relative h-40 w-full text-left" style={{ perspective: '900px' }}>
      <span className="absolute inset-0 block transition-transform duration-500" style={{ transformStyle: 'preserve-3d', transform: flipped ? 'rotateY(180deg)' : 'none' }}>
        <span className="absolute inset-0 flex flex-col justify-between rounded-xl border-2 border-[#191919] p-4 text-[#191919]"
              style={{ background: i % 3 === 0 ? 'var(--acid)' : i % 3 === 1 ? 'var(--mint-soft)' : 'var(--teal)', backfaceVisibility: 'hidden', boxShadow: '4px 4px 0 #000' }}>
          <span className="wide text-2xl font-black uppercase leading-none">{term}</span>
          <span className="mono text-[0.625rem] font-bold uppercase">tap to flip ↻</span>
        </span>
        <span className="absolute inset-0 flex flex-col rounded-xl border-2 border-[#191919] p-4"
              style={{ background: '#191919', color: '#ececed', backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}>
          <span className="mono text-[0.6875rem] font-bold uppercase text-[var(--acid)]">{full}</span>
          <span className="mt-2 text-[0.875rem] leading-snug">{body}</span>
        </span>
      </span>
    </motion.button>
  )
}

export function Glossary() {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
      {GLOSSARY.map(([t, f, b], i) => <FlipCard key={t} term={t} full={f} body={b} i={i} />)}
    </div>
  )
}
