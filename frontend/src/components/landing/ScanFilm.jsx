import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { FileText, Hash, ShieldQuestion, Upload, Waveform } from '../ui/Icons'

/**
 * Pinned horizontal "film": while the section scrolls vertically, five panels
 * slide sideways, one per stage of a scan. On phones (and with reduced motion)
 * the panels simply stack.
 */

const PANELS = [
  { n: '01', title: 'Drop', icon: Upload, bg: 'var(--acid)',
    body: 'An image, voice clip or video. Type, size and length are checked in your browser and again on the server.' },
  { n: '02', title: 'Fingerprint', icon: Hash, bg: 'var(--mint-soft)',
    body: 'A SHA-256 hash of the exact bytes is recorded and printed on the report.' },
  { n: '03', title: 'Score', icon: Waveform, bg: 'var(--teal)',
    body: 'The models for that media type score it: scene detectors for images, pellav2 for audio, GenD for faces in video.' },
  { n: '04', title: 'Decide', icon: ShieldQuestion, bg: '#ffb020',
    body: 'Two cut-offs turn the score into a verdict. In between, the honest answer is inconclusive.' },
  { n: '05', title: 'Report', icon: FileText, bg: '#ececed',
    body: 'Verdict, evidence and limits on screen and in a PDF. Delete the scan and every file goes with it.' },
]

// Little animated scene inside each panel.
function Scene({ i }) {
  if (i === 0) {
    return (
      <div className="relative h-full">
        <motion.div className="absolute left-1/2 top-0 h-20 w-16 -translate-x-1/2 rounded-md border-2 border-[#191919] bg-[#ececed]"
                    animate={{ y: [0, 70, 70, 0] }} transition={{ repeat: Infinity, duration: 2.6, times: [0, 0.4, 0.8, 1] }}>
          <span className="absolute inset-x-2 top-3 h-1.5 bg-[#191919]" /><span className="absolute inset-x-2 top-6 h-1.5 bg-[#191919] opacity-50" />
        </motion.div>
        <div className="absolute inset-x-6 bottom-2 h-12 rounded-md border-2 border-dashed border-[#191919]" />
      </div>
    )
  }
  if (i === 1) {
    return (
      <div className="mono grid h-full grid-cols-8 content-center gap-1 text-[0.75rem] font-bold">
        {'3a7b8e1f0c92d54e8b3a7f29104c8e76a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0'.match(/.{2}/g).map((b, k) => (
          <motion.span key={k} className="rounded-sm bg-[#191919] py-1 text-center text-[var(--acid)]"
                       animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 2, delay: k * 0.05 }}>{b}</motion.span>
        ))}
      </div>
    )
  }
  if (i === 2) {
    return (
      <div className="flex h-full items-end gap-2 px-2">
        {[0.35, 0.8, 0.55, 0.9, 0.4, 0.7, 0.62].map((h, k) => (
          <motion.span key={k} className="flex-1 rounded-t-sm border-2 border-b-0 border-[#191919] bg-[#191919]"
                       animate={{ height: [`${h * 40}%`, `${h * 100}%`, `${h * 40}%`] }} transition={{ repeat: Infinity, duration: 1.8, delay: k * 0.12 }} />
        ))}
      </div>
    )
  }
  if (i === 3) {
    return (
      <div className="flex h-full flex-col justify-center">
        <div className="relative h-10 overflow-hidden rounded-md border-2 border-[#191919]">
          <span className="absolute inset-y-0 left-0 w-[42%] bg-[var(--acid)]" />
          <span className="absolute inset-y-0 left-[42%] w-[16%]" style={{ background: 'repeating-linear-gradient(45deg,#191919 0 6px,transparent 6px 12px)' }} />
          <span className="absolute inset-y-0 left-[58%] right-0 bg-[#ff4d3d]" />
          <motion.span className="absolute inset-y-[-4px] w-1.5 bg-[#191919]" animate={{ left: ['10%', '50%', '85%', '50%', '10%'] }}
                       transition={{ repeat: Infinity, duration: 4, ease: 'easeInOut' }} />
        </div>
        <div className="mono mt-2 flex justify-between text-[0.6875rem] font-bold"><span>real</span><span>unsure</span><span>fake</span></div>
      </div>
    )
  }
  return (
    <div className="flex h-full items-center justify-center">
      <motion.div className="relative h-36 w-28 rounded-md border-2 border-[#191919] bg-white p-3"
                  animate={{ rotate: [-4, 3, -4] }} transition={{ repeat: Infinity, duration: 3 }}>
        <span className="block h-2 w-3/4 bg-[#191919]" />
        <span className="mt-2 block h-6 w-full bg-[var(--acid)]" />
        {[0, 1, 2, 3].map((k) => <span key={k} className="mt-1.5 block h-1 w-full bg-[#191919] opacity-40" />)}
        <span className="mono absolute bottom-2 left-3 text-[0.5rem] font-bold">PDF</span>
      </motion.div>
    </div>
  )
}

function Panel({ p, i }) {
  return (
    <article className="flex h-[min(70vh,34rem)] w-[min(82vw,30rem)] shrink-0 flex-col rounded-2xl border-2 border-[#191919] p-6 text-[#191919] sm:p-8"
             style={{ background: p.bg, boxShadow: '10px 10px 0 #000' }}>
      <div className="flex items-start justify-between">
        <span className="wide text-7xl font-black leading-none" style={{ letterSpacing: '-0.06em' }}>{p.n}</span>
        <span className="grid h-12 w-12 place-items-center rounded-md border-2 border-[#191919] bg-[#191919] text-[var(--acid)]"><p.icon size={22} /></span>
      </div>
      <div className="my-5 min-h-0 flex-1"><Scene i={i} /></div>
      <h3 className="wide text-4xl font-black uppercase leading-none tracking-tight">{p.title}</h3>
      <p className="mt-3 text-[1rem] font-medium leading-relaxed">{p.body}</p>
    </article>
  )
}

export default function ScanFilm() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] })
  const x = useTransform(scrollYProgress, [0, 1], ['0%', '-62%'])
  const bar = useTransform(scrollYProgress, [0, 1], ['0%', '100%'])

  return (
    <>
      {/* desktop: pinned, scroll-driven */}
      <section ref={ref} className="bleed relative hidden h-[320vh] motion-safe:lg:block" aria-label="How a scan runs">
        <div className="sticky top-16 flex h-[calc(100vh-4rem)] flex-col justify-center overflow-hidden">
          <div className="mx-auto mb-8 flex w-full max-w-content items-end justify-between px-10">
            <div>
              <span className="eyebrow">How a scan runs</span>
              <h2 className="wide mt-3 font-black uppercase" style={{ fontSize: 'clamp(2.25rem, 4.6vw, 4.5rem)', lineHeight: 0.92, letterSpacing: '-0.05em' }}>
                Five frames, <span className="serif-i normal-case text-gradient">one</span> scan.
              </h2>
            </div>
            <span className="mono text-[0.75rem] font-bold uppercase text-ink-muted">keep scrolling →</span>
          </div>
          <motion.div style={{ x }} className="flex gap-8 pl-10">
            {PANELS.map((p, i) => <Panel key={p.n} p={p} i={i} />)}
          </motion.div>
          <div className="mx-auto mt-10 h-1.5 w-full max-w-content px-10">
            <div className="h-full rounded-full" style={{ background: 'var(--border-strong)' }}>
              <motion.div className="h-full rounded-full" style={{ width: bar, background: 'var(--acid)' }} />
            </div>
          </div>
        </div>
      </section>

      {/* phones, tablets and reduced motion: a plain stack */}
      <section className="py-16 lg:hidden motion-reduce:lg:block">
        <span className="eyebrow">How a scan runs</span>
        <h2 className="wide mt-3 font-black uppercase" style={{ fontSize: 'clamp(2rem, 7vw, 3.5rem)', lineHeight: 0.92, letterSpacing: '-0.05em' }}>
          Five frames, <span className="serif-i normal-case text-gradient">one</span> scan.
        </h2>
        <div className="mt-8 flex flex-col items-center gap-8">
          {PANELS.map((p, i) => <Panel key={p.n} p={p} i={i} />)}
        </div>
      </section>
    </>
  )
}
