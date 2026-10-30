import { useState } from 'react'
import { motion } from 'framer-motion'
import { Cpu, Database, FileText, Globe, Network, Search } from '../ui/Icons'
import { Src } from './Sections'

// More How it works chapters: numbers board, project explorer, FAQ.
// Numbers come from docs/models/MODEL_CARD.md and docs/research/EVALUATION.md.

const ease = [0.2, 0.9, 0.3, 1]
const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.6, delay, ease },
})

// ─── By the numbers ─────────────────────────────────────────────────────────

const NUMBERS = [
  [3, '', 'media types', 'image · audio · video', 'MODEL_CARD.md'],
  [17, '', 'API routes', 'auth, upload, jobs, reports, history', 'backend/app/routers'],
  [34, '', 'analysis stages', 'every one named in chapter 07', 'backend/app/ml'],
  [71237, '', 'audio test clips', 'ASVspoof 2019 LA eval, scored once', 'EVALUATION.md §1'],
  [400, '', 'test videos', 'DFD: 200 real, 200 face swaps', 'EVALUATION.md §6'],
  [2134, '', 'newest-generator test images', 'FLUX.2, GPT Image 2, Nano Banana 2, Qwen', 'EVALUATION.md §5'],
  [580.5, 'M', 'parameters in pellav2', 'the audio verdict model', 'MODEL_CARD.md'],
  [144065, '', 'parameters in the LCNN', 'the fallback audio model', 'MODEL_CARD.md'],
]

function Counter({ to, suffix }) {
  const [v, setV] = useState(0)
  const decimals = String(to).includes('.') ? 1 : 0
  function run() {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setV(to); return }
    const start = performance.now()
    const tick = (now) => {
      const p = Math.min(1, (now - start) / 1400)
      setV(to * (1 - Math.pow(1 - p, 4)))
      if (p < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }
  return (
    <motion.span onViewportEnter={run} viewport={{ once: true }} className="tnum">
      {v.toLocaleString('en-GB', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}{suffix}
    </motion.span>
  )
}

export function NumbersBoard() {
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border-2 border-[#191919] bg-[#191919] lg:grid-cols-4"
         style={{ boxShadow: '10px 10px 0 var(--acid)' }}>
      {NUMBERS.map(([n, suf, label, hint, src], i) => (
        <div key={label} className="group relative p-5 transition-colors duration-300 hover:bg-[var(--acid)] hover:text-[#191919] sm:p-7"
             style={{ background: i % 3 === 0 ? 'var(--surface-2)' : 'var(--surface-1)' }}>
          <span className="wide block font-black leading-none" style={{ fontSize: 'clamp(1.75rem, 4vw, 3.5rem)', letterSpacing: '-0.05em' }}>
            <Counter to={n} suffix={suf} />
          </span>
          <span className="mt-2 block text-[0.875rem] font-bold uppercase sm:text-[0.9375rem]">{label}</span>
          <span className="mt-1 block text-[0.8125rem] opacity-70">{hint}</span>
          <span className="mono mt-3 block text-[0.5625rem] opacity-50">SRC {src}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Project explorer ───────────────────────────────────────────────────────

const TREE = [
  { path: 'backend/app/', icon: Network, what: 'The FastAPI service.', items: [
    ['routers/', 'auth, upload, jobs, history, health: the 17 API routes'],
    ['ml/', 'image, audio and video pipelines, model registry, verdict rules'],
    ['ml/forensics/', 'signal-level image checks: CFA, tampering, steganography, metadata, watermark'],
    ['ml/audio/', 'pellav2, the LCNN, and the audio context checks'],
    ['ml/video/', 'GenD face model, optical flow, rPPG, lip sync, container checks'],
    ['report/', 'PDF report generator and its charts'],
    ['worker/', 'Celery app and the analysis task'],
    ['retention.py · signing.py', 'guest-scan clean-up; 5-minute signed links'],
  ] },
  { path: 'frontend/src/', icon: Globe, what: 'This website.', items: [
    ['pages/', 'Landing, Analyse, Result, Report, History, How it works, Privacy, Sign in'],
    ['components/', 'per-media result views, interactive pieces, shared UI'],
    ['lib/', 'API client (cookies, signed links, WebSocket), auth, theme'],
    ['../e2e/', 'Playwright browser tests'],
  ] },
  { path: 'ml/', icon: Cpu, what: 'Training and evaluation code.', items: [
    ['training/', 'train_asvspoof.py, finetune_commfor.py, finetune_pellav2.py, calibration scripts'],
    ['preprocessing/', 'dataset builders: ASVspoof 2019 LA, In-the-Wild, faces, audio codecs'],
    ['evaluation/', 'EER, t-DCF and AUC metrics; detector and codec evaluations'],
  ] },
  { path: 'evaluation/ + paper_results/', icon: Search, what: 'The evidence behind every number.', items: [
    ['E2E-01 to E2E-03', 'full-pipeline verdict runs on held-out test sets'],
    ['COMMFOR-*', 'image detector weighting and fine-tune comparisons'],
    ['VIDEO-GEND-01', 'GenD and video verdicts on DFD'],
    ['paper_results/', 'per-item score files the results/ JSON is rebuilt from'],
  ] },
  { path: 'results/', icon: FileText, what: 'Published numbers and figures.', items: [
    ['audio_eval.json', 'ASVspoof 2019 LA eval: EER, min t-DCF, AUC'],
    ['robustness.json · latency.json', 'codec robustness and timing'],
    ['figures/', 'ROC, robustness, verdict and latency plots (shown in chapter 10)'],
  ] },
  { path: 'checkpoints/ docs/ scripts/', icon: Database, what: 'Weights, documentation, tooling.', items: [
    ['checkpoints/', 'model weights, checked by SHA-256 before loading'],
    ['docs/', 'model card, evaluation, datasets, security, setup guides'],
    ['scripts/', 'regenerate_results.py, eval_image.py, benchmark_latency.py, robustness.py'],
    ['docker-compose.yml', 'the six-container production setup'],
  ] },
]

export function ProjectExplorer() {
  const [open, setOpen] = useState(0)
  const node = TREE[open]
  return (
    <motion.div {...reveal()} className="grid overflow-hidden rounded-2xl border-2 border-[#191919] lg:grid-cols-[18rem_1fr]"
                style={{ boxShadow: '10px 10px 0 var(--teal)' }}>
      <div className="border-b-2 border-[#191919] lg:border-b-0 lg:border-r-2" style={{ background: '#191919' }}>
        <p className="mono border-b-2 border-[#333337] px-4 py-3 text-[0.6875rem] font-bold uppercase text-[#8a8a92]">deepsentinel/</p>
        <ul className="p-2">
          {TREE.map((t, i) => (
            <li key={t.path}>
              <button onClick={() => setOpen(i)} aria-pressed={open === i}
                      className="mono flex w-full items-center gap-2.5 rounded-md px-3 py-2.5 text-left text-[0.8125rem] font-bold transition-colors"
                      style={{ background: open === i ? 'var(--acid)' : 'transparent', color: open === i ? '#191919' : '#ececed' }}>
                <t.icon size={15} />
                <span className="truncate">{t.path}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
      <motion.div key={open} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}
                  className="p-6 sm:p-8" style={{ background: 'var(--surface-1)' }}>
        <h3 className="mono text-xl font-bold text-accent">{node.path}</h3>
        <p className="mt-1 text-[1rem] text-ink-secondary">{node.what}</p>
        <ul className="mt-5">
          {node.items.map(([name, desc], i) => (
            <motion.li key={name} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                       className="grid gap-1 border-b border-dashed py-3 sm:grid-cols-[14rem_1fr] sm:gap-4" style={{ borderColor: 'var(--border-strong)' }}>
              <span className="mono text-[0.8125rem] font-bold text-ink-primary">├─ {name}</span>
              <span className="text-[0.875rem] text-ink-secondary">{desc}</span>
            </motion.li>
          ))}
        </ul>
        <Src>README.md (project structure) and the folders themselves</Src>
      </motion.div>
    </motion.div>
  )
}

// ─── FAQ ────────────────────────────────────────────────────────────────────

const FAQ = [
  ['Can DeepSentinel prove a photo is real?', '“No manipulation detected” means the detectors found nothing, not that the file is genuine. Without camera metadata its origin cannot be confirmed.'],
  ['Can I use the report as legal evidence?', 'No. It is an automated technical assessment, not a certified forensic or legal opinion. Treat it as a lead for a qualified examiner.'],
  ['Why did I get inconclusive?', 'The score fell between the two cut-offs, where the detectors are not reliable enough to make a call. The newest image generators often land here.'],
  ['Which AI image generators does it catch?', 'On the test set: nearly all DALL·E, Firefly, Midjourney v5 and Stable Diffusion images, but far fewer from GPT Image 2 and Nano Banana 2. Chapter 10 has the per-generator chart.'],
  ['Does it work on phone calls or voice notes?', 'Less reliably. Narrowband and heavily compressed audio can mislead the audio models (KNOWN_ISSUES #14 and #16).'],
  ['What happens to my file?', 'It is stored to run the analysis. Delete the scan and the upload, every evidence file and the report go with it. Guest scans are deleted automatically after the retention window.'],
  ['Can it detect a fully AI-generated video?', 'The video pipeline runs the scene detectors on sampled frames, but there is no labelled test set for fully generated video yet, so this has not been measured.'],
  ['Who decided the thresholds?', 'They were chosen on development data and written down before the test sets were scored, so the test numbers were not tuned to look good.'],
]

export function Faq() {
  const [open, setOpen] = useState(0)
  return (
    <div className="space-y-3">
      {FAQ.map(([q, a], i) => (
        <motion.div key={q} {...reveal(i * 0.03)} className="overflow-hidden rounded-xl border-2 transition-shadow"
                    style={{ borderColor: open === i ? '#191919' : 'var(--border-strong)', boxShadow: open === i ? '6px 6px 0 var(--acid)' : 'none' }}>
          <button onClick={() => setOpen(open === i ? -1 : i)} aria-expanded={open === i}
                  className="flex w-full items-center justify-between gap-4 p-5 text-left transition-colors"
                  style={{ background: open === i ? 'var(--acid)' : 'var(--surface-1)', color: open === i ? '#191919' : undefined }}>
            <span className="wide text-[1rem] font-black uppercase leading-tight sm:text-lg">{q}</span>
            <motion.span animate={{ rotate: open === i ? 45 : 0 }}
                         className="grid h-8 w-8 shrink-0 place-items-center rounded-md border-2 border-current text-xl font-black leading-none">+</motion.span>
          </button>
          <motion.div initial={false} animate={{ height: open === i ? 'auto' : 0 }} transition={{ duration: 0.3, ease }}
                      style={{ overflow: 'hidden', background: 'var(--surface-1)' }}>
            <p className="p-5 pt-4 text-[1rem] leading-relaxed text-ink-secondary">{a}</p>
          </motion.div>
        </motion.div>
      ))}
    </div>
  )
}
