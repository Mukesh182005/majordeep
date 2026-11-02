import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, Clock, Cpu, FileText, Hash, Spinner } from './ui/Icons'

/**
 * Waiting screen while a job runs. It only shows what the server reports: the
 * job status (queued → processing → done) arrives over the live-status socket,
 * and the server has no finer progress than that, so there is no percentage bar.
 * The timer and the event log use the visitor's own clock.
 *
 * Loops use framer-motion with explicit transitions, so they still run on the
 * calm verdict route (where looping CSS animation is switched off).
 */

const STEPS = [
  { id: 'stored', icon: Hash, title: 'Uploaded & fingerprinted', body: 'The file is stored and its SHA-256 recorded.' },
  { id: 'queued', icon: Clock, title: 'Waiting for a worker', body: 'Your job is in the queue.' },
  { id: 'processing', icon: Cpu, title: 'Running the detectors', body: 'The models for this media type are scoring the file.' },
  { id: 'done', icon: FileText, title: 'Writing the result', body: 'Verdict, evidence and report are being saved.' },
]

// Facts from docs/models/MODEL_CARD.md and docs/research/EVALUATION.md §4.
const TIPS = [
  ['Borderline is allowed', 'If the score falls between the two cut-offs, the verdict is "inconclusive" rather than a forced real or fake.'],
  ['Typical timings', 'On the test machine an image takes about half a second on CPU, a clip of speech about a second, and a face-swap check on a short video around 20 seconds.'],
  ['First scan is slower', 'The worker loads each model the first time it is needed, so the very first analysis takes longer than the next ones.'],
  ['Evidence, not just a score', 'The result page shows which detectors decided the verdict and which checks are only shown as unvalidated context.'],
  ['You stay in control', 'Delete a scan and its upload, every evidence file and its report are removed with it.'],
]

function stepIndex(status) {
  if (status === 'done') return 3
  if (status === 'processing') return 2
  return 1 // queued, or nothing heard yet
}

function fmt(ms) {
  const s = Math.floor(ms / 1000)
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

/** The animated "scan bay": a document being swept by a scanner beam. */
function ScanBay({ status }) {
  const running = status !== 'done'
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[19rem]" aria-hidden="true">
      {/* orbit rings */}
      {[1, 0.78].map((s, i) => (
        <motion.div key={s} className="absolute rounded-full border-2 border-dashed"
                    style={{ inset: `${(1 - s) * 50}%`, borderColor: i ? 'var(--teal)' : 'var(--border-strong)' }}
                    animate={running ? { rotate: i ? -360 : 360 } : { rotate: 0 }}
                    transition={running ? { repeat: Infinity, ease: 'linear', duration: i ? 18 : 26 } : { duration: 0.6 }}>
          <span className="absolute -top-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rounded-full border-2 border-[#191919]"
                style={{ background: i ? 'var(--teal)' : 'var(--acid)' }} />
        </motion.div>
      ))}

      {/* the document */}
      <div className="absolute inset-[24%] overflow-hidden rounded-lg border-2 border-[#191919]"
           style={{ background: '#ececed', boxShadow: '6px 6px 0 #000' }}>
        <div className="absolute inset-x-[14%] top-[14%] h-[10%] rounded-sm bg-[#191919]" />
        <div className="absolute inset-x-[14%] top-[30%] h-[28%] rounded-sm" style={{ background: 'var(--mint-soft)' }} />
        {[66, 74, 82].map((t, i) => (
          <div key={t} className="absolute left-[14%] h-[4%] rounded-sm bg-[#191919] opacity-40" style={{ top: `${t}%`, right: `${14 + i * 12}%` }} />
        ))}

        {/* scanner beam */}
        {running && (
          <motion.div className="absolute inset-x-0 h-[22%]"
                      style={{ background: 'linear-gradient(180deg, transparent, rgba(35,248,113,.35) 80%, rgba(35,248,113,.95))' }}
                      initial={{ top: '-22%' }} animate={{ top: ['-22%', '100%'] }}
                      transition={{ repeat: Infinity, duration: 2.2, ease: 'easeInOut', repeatType: 'reverse' }} />
        )}

        {/* finished stamp */}
        <AnimatePresence>
          {!running && (
            <motion.div initial={{ scale: 2, opacity: 0, rotate: -20 }} animate={{ scale: 1, opacity: 1, rotate: -8 }}
                        transition={{ type: 'spring', stiffness: 260, damping: 14 }}
                        className="absolute inset-0 grid place-items-center">
              <span className="grid h-16 w-16 place-items-center rounded-full border-4 border-[#191919] bg-[var(--acid)] text-[#191919]">
                <Check size={30} />
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* sparks around the document while running */}
      {running && [0, 1, 2, 3].map((i) => (
        <motion.span key={i} className="absolute h-2 w-2 rounded-full"
                     style={{ background: i % 2 ? 'var(--acid)' : 'var(--teal)', left: `${[20, 78, 74, 18][i]}%`, top: `${[22, 26, 74, 70][i]}%` }}
                     animate={{ opacity: [0, 1, 0], scale: [0.4, 1.3, 0.4] }}
                     transition={{ repeat: Infinity, duration: 1.8, delay: i * 0.45 }} />
      ))}
    </div>
  )
}

export default function AnalysisProgress({ liveStatus }) {
  const status = liveStatus?.status || 'queued'
  const active = stepIndex(status)
  const startedAt = useRef(Date.now())
  const [now, setNow] = useState(Date.now())
  const [tip, setTip] = useState(0)
  const [log, setLog] = useState(() => [{ at: Date.now(), text: 'Job created; waiting for the first status update' }])

  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000)
    const c = window.setInterval(() => setTip((v) => (v + 1) % TIPS.length), 6000)
    return () => { window.clearInterval(t); window.clearInterval(c) }
  }, [])

  // One log line per real status change.
  const lastStatus = useRef(null)
  useEffect(() => {
    if (!liveStatus?.status || liveStatus.status === lastStatus.current) return
    lastStatus.current = liveStatus.status
    const text = {
      queued: 'In the queue, waiting for a worker',
      processing: 'A worker picked up the job and started the detectors',
      done: 'Analysis finished; loading the result',
      failed: 'The analysis failed',
    }[liveStatus.status] || liveStatus.message || liveStatus.status
    setLog((l) => [...l, { at: Date.now(), text }])
  }, [liveStatus])

  return (
    <div className="mx-auto max-w-5xl animate-in" data-testid="analysis-progress">
      <div className="overflow-hidden rounded-2xl border-2 border-[#191919]" style={{ background: 'var(--surface-1)' }}>
        {/* header strip */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-[#191919] px-5 py-3"
             style={{ background: 'var(--acid)', color: '#191919' }}>
          <span className="mono flex items-center gap-2 text-[0.75rem] font-bold uppercase">
            {status === 'done' ? <Check size={14} /> : <Spinner size={14} />} {liveStatus?.message || 'Connecting…'}
          </span>
          <span className="mono tnum rounded-md bg-[#191919] px-2.5 py-1 text-[0.8125rem] font-bold text-[var(--acid)]" aria-label="Elapsed time">
            {fmt(now - startedAt.current)}
          </span>
        </div>

        <div className="grid gap-8 p-6 sm:p-10 lg:grid-cols-[1fr_1.15fr] lg:items-center">
          <div>
            <ScanBay status={status} />
            <h2 className="mt-6 text-center text-2xl font-black tracking-tight text-ink-primary">
              {status === 'done' ? 'Done. Opening your result…' : status === 'processing' ? 'Looking closely at your file…' : 'Getting your file in line…'}
            </h2>
            <p className="mt-2 text-center text-[0.9375rem] text-ink-secondary">
              You can leave this page: the analysis keeps running and this link stays valid.
            </p>
          </div>

          <div className="space-y-6">
            {/* real stage tracker */}
            <ol className="space-y-3" aria-label="Analysis stages">
              {STEPS.map((s, i) => {
                const state = i < active ? 'done' : i === active ? 'now' : 'next'
                return (
                  <motion.li key={s.id} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}
                             className="flex items-start gap-3 rounded-xl border-2 p-3.5"
                             style={{
                               borderColor: state === 'now' ? '#191919' : 'var(--border-subtle)',
                               background: state === 'now' ? 'var(--mint-soft)' : 'var(--surface-2)',
                               color: state === 'now' ? '#191919' : undefined,
                               opacity: state === 'next' ? 0.55 : 1,
                             }}
                             aria-current={state === 'now' ? 'step' : undefined}>
                    <span className="relative grid h-9 w-9 shrink-0 place-items-center rounded-md border-2 border-[#191919]"
                          style={{ background: state === 'done' ? 'var(--acid)' : state === 'now' ? '#191919' : 'var(--surface-3)', color: state === 'now' ? 'var(--acid)' : '#191919' }}>
                      {state === 'done' ? <Check size={16} /> : <s.icon size={16} />}
                      {state === 'now' && (
                        <motion.span className="absolute inset-[-5px] rounded-lg border-2 border-[var(--acid)]"
                                     animate={{ opacity: [0.9, 0, 0.9], scale: [1, 1.18, 1] }}
                                     transition={{ repeat: Infinity, duration: 1.8 }} />
                      )}
                    </span>
                    <span>
                      <span className="block font-bold">{s.title}</span>
                      <span className="block text-[0.8125rem] opacity-75">{s.body}</span>
                    </span>
                  </motion.li>
                )
              })}
            </ol>

            {/* real event log */}
            <div className="rounded-xl border-2 border-[#191919] bg-[#191919] p-4">
              <p className="mono mb-2 text-[0.625rem] font-bold uppercase tracking-wider text-[#8a8a92]">Event log · your clock</p>
              <ul className="mono space-y-1 text-[0.75rem]" aria-live="polite">
                {log.map((l) => (
                  <motion.li key={l.at + l.text} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="flex gap-3 text-[#a7e1c5]">
                    <span className="text-[#56565c]">{new Date(l.at).toLocaleTimeString([], { hour12: false })}</span>
                    <span>{l.text}</span>
                  </motion.li>
                ))}
              </ul>
            </div>

            {/* rotating tips */}
            <div className="relative min-h-[6.5rem] overflow-hidden rounded-xl border-2 p-4" style={{ borderColor: 'var(--border-strong)' }}>
              <p className="mono text-[0.625rem] font-bold uppercase tracking-wider text-accent">While you wait · {tip + 1}/{TIPS.length}</p>
              <AnimatePresence mode="wait">
                <motion.div key={tip} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.35 }}>
                  <p className="mt-1.5 font-bold text-ink-primary">{TIPS[tip][0]}</p>
                  <p className="mt-0.5 text-[0.875rem] leading-relaxed text-ink-secondary">{TIPS[tip][1]}</p>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
