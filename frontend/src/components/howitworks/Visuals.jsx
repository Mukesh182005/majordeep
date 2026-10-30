import { useState } from 'react'
import { motion } from 'framer-motion'
import { Src } from './Sections'

// Diagrams and charts for the How it works page. Every value is copied from
// the file named in its SRC line.

const ease = [0.2, 0.9, 0.3, 1]
const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.6, delay, ease },
})

const INK = '#191919'
const ACID = '#23f871'
const MINT = '#a7e1c5'
const TEAL = '#43b6a1'
const RED = '#ff4d3d'
const AMBER = '#ffb020'

// ─── 1 · System map ─────────────────────────────────────────────────────────

const NODES = {
  browser: { x: 30, y: 230, w: 130, label: 'Browser', sub: 'React app', fill: '#ececed',
    info: 'The website you are on. It talks to the API over HTTPS and listens to live job progress on a WebSocket.' },
  nginx: { x: 215, y: 230, w: 130, label: 'frontend', sub: 'nginx', fill: ACID,
    info: 'Serves the built React app and forwards every /api request to the API container.' },
  api: { x: 400, y: 230, w: 130, label: 'api', sub: 'FastAPI', fill: MINT,
    info: 'Checks and stores uploads, hashes them, creates the job, serves results, reports and signed links. Holds no models.' },
  redis: { x: 600, y: 80, w: 130, label: 'redis', sub: 'job queue', fill: '#ececed',
    info: 'The queue between api and worker. A new upload becomes a task here.' },
  worker: { x: 800, y: 230, w: 140, label: 'worker', sub: 'Celery + PyTorch', fill: TEAL,
    info: 'Picks up tasks, loads the models once, runs the image, audio or video pipeline, writes the verdict and evidence.' },
  models: { x: 800, y: 60, w: 140, label: 'models', sub: 'checkpoints + HF cache', fill: '#ececed',
    info: 'Model weights on disk, checked by SHA-256 before loading; Hugging Face downloads cached in a named volume.' },
  db: { x: 600, y: 400, w: 130, label: 'db', sub: 'PostgreSQL', fill: MINT,
    info: 'Tables users, jobs, reports and upload_events. Evidence is stored as JSON on each job.' },
  files: { x: 800, y: 400, w: 140, label: 'media', sub: 'uploads · evidence · PDFs', fill: '#ececed',
    info: 'Uploaded files, heatmaps and other evidence images, and generated PDF reports.' },
  beat: { x: 400, y: 420, w: 130, label: 'beat', sub: 'scheduler', fill: AMBER,
    info: 'Runs on a timer and deletes guest jobs older than the retention window: upload, evidence and report.' },
}

const EDGES = [
  ['browser', 'nginx', 'HTTPS'],
  ['nginx', 'api', '/api'],
  ['api', 'redis', 'enqueue'],
  ['redis', 'worker', 'task'],
  ['models', 'worker', 'load once'],
  ['worker', 'db', 'verdict'],
  ['worker', 'files', 'evidence'],
  ['api', 'db', 'jobs, users'],
  ['api', 'files', 'store upload'],
  ['beat', 'db', 'purge'],
  ['beat', 'files', 'purge'],
]

const H = 56
const center = (n) => [NODES[n].x + NODES[n].w / 2, NODES[n].y + H / 2]

function edgePath(a, b) {
  const [x1, y1] = center(a)
  const [x2, y2] = center(b)
  const mx = (x1 + x2) / 2
  return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`
}

export function SystemMap() {
  const [hover, setHover] = useState('worker')
  const linked = (e) => e[0] === hover || e[1] === hover

  return (
    <motion.div {...reveal()} className="overflow-hidden rounded-2xl border-2 border-[#191919]" style={{ background: '#191919', boxShadow: '10px 10px 0 var(--acid)' }}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-[#333337] px-4 py-3" style={{ background: '#28282b' }}>
        <span className="mono text-[0.75rem] font-bold uppercase text-[#a7a7ab]">System map · docker compose · hover a box</span>
        <span className="mono flex items-center gap-2 text-[0.6875rem] text-[#8a8a92]"><span className="h-2 w-2 rounded-full bg-[var(--acid)]" /> live data flow</span>
      </div>
      <div className="grid lg:grid-cols-[1fr_18rem]">
        <div className="overflow-x-auto">
          <svg viewBox="0 0 980 500" className="min-w-[720px]" role="img" aria-label="Diagram of the DeepSentinel deployment">
            <defs>
              <pattern id="sm-grid" width="28" height="28" patternUnits="userSpaceOnUse">
                <path d="M28 0H0V28" fill="none" stroke="#28282b" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width="980" height="500" fill="url(#sm-grid)" />

            {EDGES.map((e, i) => {
              const d = edgePath(e[0], e[1])
              const on = linked(e)
              const [x1, y1] = center(e[0])
              const [x2, y2] = center(e[1])
              return (
                <g key={i}>
                  <path d={d} fill="none" stroke={on ? ACID : '#444449'} strokeWidth={on ? 3 : 2} strokeDasharray={on ? '0' : '6 6'} />
                  <circle r={on ? 5 : 3.5} fill={on ? ACID : MINT}>
                    <animateMotion dur={`${2.2 + (i % 4) * 0.4}s`} repeatCount="indefinite" path={d} />
                  </circle>
                  <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 8} textAnchor="middle" fontFamily="Space Mono, monospace" fontSize="11"
                        fontWeight="700" fill={on ? ACID : '#8a8a92'}>{e[2]}</text>
                </g>
              )
            })}

            {Object.entries(NODES).map(([id, n]) => (
              <g key={id} onMouseEnter={() => setHover(id)} onFocus={() => setHover(id)} tabIndex={0} style={{ cursor: 'pointer', outline: 'none' }}>
                <rect x={n.x + 5} y={n.y + 5} width={n.w} height={H} rx="8" fill={hover === id ? ACID : '#000'} />
                <rect x={n.x} y={n.y} width={n.w} height={H} rx="8" fill={n.fill} stroke={INK} strokeWidth="2.5" />
                <text x={n.x + 12} y={n.y + 24} fontFamily="Archivo, sans-serif" fontWeight="900" fontSize="16" fill={INK}>{n.label}</text>
                <text x={n.x + 12} y={n.y + 42} fontFamily="Space Mono, monospace" fontSize="10.5" fill={INK} opacity="0.75">{n.sub}</text>
              </g>
            ))}
          </svg>
        </div>
        <motion.div key={hover} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
                    className="border-t-2 border-[#333337] p-5 text-[#ececed] lg:border-l-2 lg:border-t-0">
          <span className="mono text-[0.6875rem] font-bold uppercase text-[var(--acid)]">{NODES[hover].sub}</span>
          <h3 className="wide mt-1 text-3xl font-black uppercase leading-none">{NODES[hover].label}</h3>
          <p className="mt-4 text-[0.9375rem] leading-relaxed text-[#a7e1c5]">{NODES[hover].info}</p>
          <p className="mono mt-5 text-[0.6875rem] text-[#8a8a92]">Connects to: {EDGES.filter(linked).map((e) => (e[0] === hover ? e[1] : e[0])).join(', ')}</p>
        </motion.div>
      </div>
      <div className="px-4 pb-4"><Src light>docker-compose.yml · docs/architecture/SYSTEM_ARCHITECTURE.md · frontend/nginx.conf</Src></div>
    </motion.div>
  )
}

// ─── 3 · Audio windowing ────────────────────────────────────────────────────

const WIN_SCORES = [0.31, 0.44, 0.72, 0.81, 0.66, 0.58, 0.49, 0.62] // illustrative

export function AudioWindows() {
  const [run, setRun] = useState(0)
  const mean = WIN_SCORES.reduce((a, b) => a + b, 0) / WIN_SCORES.length
  return (
    <motion.div {...reveal()} className="rounded-2xl border-2 border-[#191919] p-5 sm:p-8" style={{ background: '#ececed', color: INK, boxShadow: '8px 8px 0 var(--teal)' }}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="mono text-[0.75rem] font-bold uppercase">Flowchart · audio windows (illustrative scores)</span>
        <button onClick={() => setRun((r) => r + 1)} className="mono rounded-md border-2 border-[#191919] bg-[#191919] px-3 py-1 text-[0.75rem] font-bold uppercase text-[var(--acid)] transition-transform hover:-translate-y-0.5">
          ↻ Replay
        </button>
      </div>

      {/* waveform cut into windows */}
      <div key={run} className="mt-6 grid grid-cols-8 gap-1.5">
        {WIN_SCORES.map((s, i) => (
          <div key={i} className="flex flex-col items-center">
            <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.12 }}
                        className="flex h-20 w-full items-center gap-[2px] rounded-md border-2 border-[#191919] bg-[#191919] px-1">
              {Array.from({ length: 9 }, (_, k) => (
                <span key={k} className="flex-1" style={{ height: `${25 + 70 * Math.abs(Math.sin((i * 9 + k) * 0.7))}%`, background: TEAL }} />
              ))}
            </motion.div>
            <span className="mono mt-1 text-[0.5625rem] font-bold">{i * 4}–{i * 4 + 4}s</span>
            <motion.div initial={{ height: 0 }} animate={{ height: `${s * 70}px` }} transition={{ delay: 0.9 + i * 0.1, duration: 0.5 }}
                        className="mt-2 w-full rounded-t-sm border-2 border-b-0 border-[#191919]"
                        style={{ background: s >= 0.58 ? RED : s < 0.42 ? ACID : AMBER }} />
            <span className="mono text-[0.625rem] font-bold">{s.toFixed(2)}</span>
          </div>
        ))}
      </div>

      <motion.div key={`m${run}`} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 1.9 }}
                  className="mx-auto mt-6 flex max-w-md items-center justify-between gap-4 rounded-lg border-2 border-[#191919] p-4"
                  style={{ background: mean >= 0.58 ? RED : mean < 0.42 ? ACID : AMBER, boxShadow: '4px 4px 0 #000' }}>
        <span className="mono text-[0.75rem] font-bold uppercase">Mean of 8 windows</span>
        <span className="wide text-3xl font-black">{mean.toFixed(2)}</span>
      </motion.div>
      <p className="mt-5 text-[0.9375rem] leading-relaxed">
        pellav2 cleans the clip (16 kHz mono, DC removal, 20 Hz high-pass), cuts it into consecutive 4-second windows (at most 8, the
        first 32 s), loudness-normalises each to −23 LUFS, scores each one, and averages them. ≥ 0.58 is AI-generated, below 0.42 is
        authentic, in between is inconclusive. The per-window scores become the timeline on the result page.
      </p>
      <Src>docs/models/MODEL_CARD.md · Audio · pellav2 (Input, Output) — window scores above are an example, not a real clip</Src>
    </motion.div>
  )
}

// ─── 4 · Radial attack chart ────────────────────────────────────────────────

const ATTACKS = { A07: 0.0018, A08: 0.0088, A09: 0.0006, A10: 0.0075, A11: 0.0030, A12: 0.0020, A13: 0.0022, A14: 0.0195, A15: 0.0200, A16: 0.0042, A17: 0.2369, A18: 0.0273, A19: 0.0283 }

export function AttackRadial() {
  const [sel, setSel] = useState('A17')
  const entries = Object.entries(ATTACKS)
  const cx = 200
  const cy = 200
  const r0 = 46
  const rMax = 180
  // square-root scale so the small bars stay visible next to A17
  const len = (v) => r0 + Math.sqrt(v / 0.25) * (rMax - r0)
  const step = (2 * Math.PI) / entries.length
  return (
    <motion.div {...reveal()} className="grid gap-6 rounded-2xl border-2 border-[#191919] p-5 sm:p-8 lg:grid-cols-[minmax(0,26rem)_1fr] lg:items-center"
                style={{ background: 'var(--surface-1)', boxShadow: '8px 8px 0 #000' }}>
      <svg viewBox="-24 -16 448 432" className="mx-auto w-full max-w-[26rem]" role="img" aria-label="Error rate per unseen attack, radial chart">
        {[0.01, 0.05, 0.1, 0.25].map((g) => (
          <g key={g}>
            <circle cx={cx} cy={cy} r={len(g)} fill="none" stroke="var(--border-strong)" strokeDasharray="3 5" />
            <text x={cx + len(g) * 0.72 + 4} y={cy + len(g) * 0.72 + 10} fontFamily="Space Mono" fontSize="9" fill="var(--text-muted)">{g * 100}%</text>
          </g>
        ))}
        {entries.map(([k, v], i) => {
          const a = i * step - Math.PI / 2
          const r = len(v)
          const x = cx + Math.cos(a) * r
          const y = cy + Math.sin(a) * r
          const on = sel === k
          const color = v > 0.1 ? RED : v > 0.015 ? AMBER : ACID
          return (
            <g key={k} onMouseEnter={() => setSel(k)} onClick={() => setSel(k)} style={{ cursor: 'pointer' }}>
              <motion.line x1={cx + Math.cos(a) * r0} y1={cy + Math.sin(a) * r0} stroke={color} strokeWidth={on ? 14 : 10} strokeLinecap="round"
                           initial={{ x2: cx + Math.cos(a) * r0, y2: cy + Math.sin(a) * r0 }}
                           whileInView={{ x2: x, y2: y }} viewport={{ once: true }} transition={{ delay: i * 0.05, duration: 0.8 }} />
              <text x={cx + Math.cos(a) * (rMax + 14)} y={cy + Math.sin(a) * (rMax + 14) + 4} textAnchor="middle"
                    fontFamily="Space Mono" fontWeight="700" fontSize="11" fill={on ? 'var(--accent)' : 'var(--text-secondary)'}>{k}</text>
            </g>
          )
        })}
        <circle cx={cx} cy={cy} r={r0 - 6} fill="#191919" stroke={ACID} strokeWidth="2" />
        <text x={cx} y={cy - 4} textAnchor="middle" fontFamily="Archivo" fontWeight="900" fontSize="20" fill={ACID}>{sel}</text>
        <text x={cx} y={cy + 16} textAnchor="middle" fontFamily="Space Mono" fontWeight="700" fontSize="13" fill="#ececed">{(ATTACKS[sel] * 100).toFixed(2)}%</text>
      </svg>
      <div>
        <span className="mono text-[0.75rem] font-bold uppercase text-accent">Radial chart · LCNN error rate per unseen attack</span>
        <h3 className="wide mt-2 text-3xl font-black uppercase leading-none">One attack in thirteen breaks it.</h3>
        <p className="mt-4 text-[1rem] leading-relaxed text-ink-secondary">
          The fallback audio model never saw attacks A07–A19 during training. On twelve of them its equal error rate stays under
          3 %. On <strong className="text-ink-primary">A17 it is 23.7 %</strong>. Hover a spoke to read its value; the radius is on
          a square-root scale so the small ones stay visible.
        </p>
        <Src>results/audio_eval.json · asvspoof2019_la_eval.per_attack_eer (served checkpoint, seed 2)</Src>
      </div>
    </motion.div>
  )
}

// ─── 5 · Waffle: video verdicts before / after ──────────────────────────────

function Waffle({ title, real, fake, realFlagged, fakeCaught, delay = 0 }) {
  const cells = [
    ...Array.from({ length: real }, (_, i) => ({ kind: 'real', hit: i < realFlagged })),
    ...Array.from({ length: fake }, (_, i) => ({ kind: 'fake', hit: i < fakeCaught })),
  ]
  const per = real + fake > 100 ? 12 : 10
  return (
    <div>
      <h4 className="wide text-lg font-black uppercase">{title}</h4>
      <div className="mt-3 grid gap-[3px]" style={{ gridTemplateColumns: `repeat(${per}, minmax(0, 1fr))` }}>
        {cells.map((c, i) => {
          const color = c.kind === 'real' ? (c.hit ? RED : ACID) : (c.hit ? TEAL : '#56565c')
          return (
            <motion.span key={i} className="aspect-square rounded-[3px] border border-[#191919]" style={{ background: color }}
                         initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }}
                         transition={{ delay: delay + i * 0.008, type: 'spring', stiffness: 400, damping: 20 }} />
          )
        })}
      </div>
      <p className="mono mt-3 text-[0.75rem] text-ink-secondary">
        real flagged <strong style={{ color: RED }}>{realFlagged}/{real}</strong> · swaps caught <strong style={{ color: TEAL }}>{fakeCaught}/{fake}</strong>
      </p>
    </div>
  )
}

export function VideoWaffles() {
  return (
    <motion.div {...reveal()} className="rounded-2xl border-2 border-[#191919] p-5 sm:p-8" style={{ background: 'var(--surface-1)', boxShadow: '8px 8px 0 #000' }}>
      <span className="mono text-[0.75rem] font-bold uppercase text-accent">Waffle chart · one square per video</span>
      <div className="mt-6 grid gap-10 md:grid-cols-2">
        <Waffle title="Old rules · 120 videos" real={60} fake={60} realFlagged={26} fakeCaught={31} />
        <Waffle title="Fixed rules + GenD · 80 held-out" real={40} fake={40} realFlagged={1} fakeCaught={29} delay={0.3} />
      </div>
      <div className="mono mt-6 flex flex-wrap gap-4 text-[0.6875rem] font-bold uppercase">
        {[[ACID, 'real, passed'], [RED, 'real, wrongly flagged'], [TEAL, 'face swap, caught'], ['#56565c', 'face swap, missed']].map(([c, l]) => (
          <span key={l} className="flex items-center gap-2"><span className="h-3.5 w-3.5 rounded-[3px] border border-[#191919]" style={{ background: c }} />{l}</span>
        ))}
      </div>
      <Src>docs/research/EVALUATION.md §6 · evaluation/VIDEO-GEND-01/summary.json (video_dfd120_gend_off, video_dfd_heldout80_gend_on)</Src>
    </motion.div>
  )
}

// ─── 6 · Dumbbell: ASVspoof 2019 vs ASVspoof 5 ──────────────────────────────

const DUMBBELLS = [
  ['Fakes caught', 97.7, 77.0, true],
  ['Real wrongly flagged', 0.3, 15.0, false],
]

export function AudioDumbbell() {
  return (
    <motion.div {...reveal()} className="rounded-2xl border-2 border-[#191919] p-5 sm:p-8" style={{ background: 'var(--surface-1)', boxShadow: '8px 8px 0 #000' }}>
      <span className="mono text-[0.75rem] font-bold uppercase text-accent">Dumbbell chart · same audio pipeline, harder test</span>
      <div className="mt-8 space-y-10">
        {DUMBBELLS.map(([label, a, b, higherBetter], i) => (
          <div key={label}>
            <p className="font-bold">{label}</p>
            <div className="relative mt-9 h-8">
              <div className="absolute inset-x-0 top-1/2 h-[2px] -translate-y-1/2" style={{ background: 'var(--border-strong)' }} />
              {[0, 25, 50, 75, 100].map((t) => (
                <span key={t} className="mono absolute top-full mt-1 -translate-x-1/2 text-[0.5625rem] text-ink-muted" style={{ left: `${t}%` }}>{t}%</span>
              ))}
              <motion.div className="absolute top-1/2 h-2 -translate-y-1/2 rounded-full" style={{ background: higherBetter ? RED : RED, left: `${Math.min(a, b)}%` }}
                          initial={{ width: 0 }} whileInView={{ width: `${Math.abs(a - b)}%` }} viewport={{ once: true }} transition={{ delay: 0.3 + i * 0.2, duration: 0.9 }} />
              <span className="absolute top-1/2 grid h-6 w-6 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-2 border-[#191919]" style={{ left: `${a}%`, background: ACID }} />
              <span className="absolute top-1/2 grid h-6 w-6 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-2 border-[#191919]" style={{ left: `${b}%`, background: AMBER }} />
              <span className="mono absolute -top-6 -translate-x-1/2 text-[0.75rem] font-bold" style={{ left: `${a}%`, color: 'var(--accent)' }}>{a}%</span>
              <span className="mono absolute -top-6 -translate-x-1/2 text-[0.75rem] font-bold" style={{ left: `${b}%`, color: AMBER }}>{b}%</span>
            </div>
          </div>
        ))}
      </div>
      <div className="mono mt-10 flex flex-wrap gap-5 text-[0.6875rem] font-bold uppercase">
        <span className="flex items-center gap-2"><span className="h-3.5 w-3.5 rounded-full border-2 border-[#191919]" style={{ background: ACID }} />ASVspoof 2019 LA eval</span>
        <span className="flex items-center gap-2"><span className="h-3.5 w-3.5 rounded-full border-2 border-[#191919]" style={{ background: AMBER }} />ASVspoof 5 eval sample</span>
        <span className="flex items-center gap-2"><span className="h-2 w-6 rounded-full" style={{ background: RED }} />the gap</span>
      </div>
      <Src>docs/research/EVALUATION.md §5a · evaluation/E2E-01/summary.json (sets.audio_*), 300 + 300 clips per set</Src>
    </motion.div>
  )
}

// ─── 7 · Model scale ────────────────────────────────────────────────────────

export function ModelScale() {
  const big = 580.5e6
  const small = 144065
  const ratio = Math.round(big / small)
  // areas drawn to scale: side ∝ √params
  const sideBig = 100
  const sideSmall = sideBig * Math.sqrt(small / big)
  return (
    <motion.div {...reveal()} className="grid gap-6 rounded-2xl border-2 border-[#191919] p-5 sm:p-8 md:grid-cols-[1fr_1.2fr] md:items-center"
                style={{ background: '#ececed', color: INK, boxShadow: '8px 8px 0 var(--acid)' }}>
      <div className="relative mx-auto aspect-square w-full max-w-[20rem]">
        <motion.div initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ type: 'spring', stiffness: 120, damping: 14 }}
                    className="absolute inset-0 origin-bottom-left rounded-md border-2 border-[#191919]" style={{ background: TEAL }}>
          <span className="wide absolute left-3 top-3 text-xl font-black uppercase">pellav2</span>
          <span className="mono absolute left-3 top-10 text-[0.75rem] font-bold">580.5 M params</span>
        </motion.div>
        <motion.div initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ delay: 0.6, type: 'spring', stiffness: 300, damping: 10 }}
                    className="absolute bottom-0 left-0 border-2 border-[#191919]" style={{ width: `${sideSmall}%`, height: `${sideSmall}%`, minWidth: 4, minHeight: 4, background: RED }} />
        <span className="mono absolute bottom-3 left-6 rounded-sm bg-[#191919] px-1.5 py-0.5 text-[0.6875rem] font-bold text-[var(--acid)]">← LCNN · 144,065</span>
      </div>
      <div>
        <span className="mono text-[0.75rem] font-bold uppercase">Drawn to scale · area = parameters</span>
        <h3 className="wide mt-2 font-black uppercase leading-none" style={{ fontSize: 'clamp(2rem, 4vw, 3.25rem)' }}>~{ratio.toLocaleString('en-GB')}× bigger</h3>
        <p className="mt-4 text-[1rem] leading-relaxed">
          The audio verdict model, pellav2, has about {ratio.toLocaleString('en-GB')} times the parameters of the LCNN that was trained here
          and now serves as its fallback. The tiny red square in the corner is the LCNN. Bigger is not automatically better:
          on MP3 the LCNN breaks, while pellav2 struggles with some neural codecs.
        </p>
        <Src>docs/models/MODEL_CARD.md · Audio (pellav2 architecture; LCNN architecture)</Src>
      </div>
    </motion.div>
  )
}

// ─── 8 · Dev decides, test judges ───────────────────────────────────────────

const SPLITS = [
  ['TRAIN', 'Learn weights', 'ASVspoof 2019 LA train (25,380 utterances) · fine-tune sets', MINT, 45],
  ['DEV', 'Make every choice', 'epoch, features, calibration, thresholds, model weights in the ensemble', ACID, 25],
  ['TEST', 'Score once', 'held-out sets nobody tuned on: LA eval, ASVspoof 5, COCO + Synthbuster test half, DFD', AMBER, 30],
]

export function DevTestFlow() {
  return (
    <motion.div {...reveal()} className="rounded-2xl border-2 border-[#191919] p-5 sm:p-8" style={{ background: 'var(--surface-1)', boxShadow: '8px 8px 0 #000' }}>
      <span className="mono text-[0.75rem] font-bold uppercase text-accent">Data discipline · dev decides, test judges</span>
      <div className="mt-6 flex h-16 overflow-hidden rounded-lg border-2 border-[#191919]">
        {SPLITS.map(([k, , , c, w], i) => (
          <motion.div key={k} className="wide grid place-items-center border-r-2 border-[#191919] text-lg font-black text-[#191919] last:border-r-0"
                      style={{ background: c }} initial={{ width: 0 }} whileInView={{ width: `${w}%` }} viewport={{ once: true }}
                      transition={{ delay: i * 0.25, duration: 0.7, ease }}>
            {k}
          </motion.div>
        ))}
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {SPLITS.map(([k, t, b, c], i) => (
          <motion.div key={k} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.6 + i * 0.1 }}
                      className="relative rounded-lg border-2 p-4" style={{ borderColor: c }}>
            <span className="mono text-[0.6875rem] font-bold" style={{ color: c }}>{String(i + 1).padStart(2, '0')} · {k}</span>
            <h4 className="wide mt-1 text-lg font-black uppercase">{t}</h4>
            <p className="mt-1 text-[0.875rem] text-ink-secondary">{b}</p>
            {i < 2 && <span className="absolute -right-4 top-1/2 hidden -translate-y-1/2 text-2xl font-black text-ink-muted md:block">→</span>}
          </motion.div>
        ))}
      </div>
      <p className="mt-5 text-[0.9375rem] text-ink-secondary">
        Two candidate upgrades were rejected this way: each looked better on dev but broke a rule fixed before the test (chapter 12).
        The bar widths are a picture of the idea, not data sizes.
      </p>
      <Src>docs/research/DATASETS.md (splits) · docs/research/EVALUATION.md (intro, §5, §5a)</Src>
    </motion.div>
  )
}
