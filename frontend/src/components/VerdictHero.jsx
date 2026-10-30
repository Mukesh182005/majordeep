import { motion } from 'framer-motion'
import { Download, FileText } from './ui/Icons'

// Verdict slab colours. Green only ever means "no manipulation detected";
// amber and signal red are the two warning colours.
function slabFor(tone, label) {
  if (tone === 'good') return { bg: 'var(--acid)', sticker: 'Clear' }
  if (/manipulated|ai-generated/i.test(label)) return { bg: '#ff4d3d', sticker: 'Flagged' }
  if (/inconclusive/i.test(label)) return { bg: '#ffb020', sticker: 'Unsure' }
  return { bg: 'var(--surface-3)', sticker: 'Pending' }
}

/** Half-circle gauge for the model score (0–100). The needle sweeps in once. */
function ScoreDial({ value }) {
  const pct = Math.max(0, Math.min(1, value))
  const angle = -90 + pct * 180
  const ticks = Array.from({ length: 11 }, (_, i) => -90 + i * 18)
  return (
    <div className="relative w-full max-w-[18rem]">
      <svg viewBox="0 0 200 116" className="w-full" role="img"
           aria-label={`Model score ${(pct * 100).toFixed(1)} percent`}>
        <path d="M 16 100 A 84 84 0 0 1 184 100" fill="none" stroke="#191919" strokeWidth="18" strokeLinecap="butt" />
        <motion.path d="M 16 100 A 84 84 0 0 1 184 100" fill="none" stroke="#ececed" strokeWidth="10"
                     initial={{ pathLength: 0 }} animate={{ pathLength: pct }}
                     transition={{ duration: 1.2, ease: [0.2, 0.9, 0.3, 1], delay: 0.2 }} />
        {ticks.map((a) => (
          <line key={a} x1="100" y1="12" x2="100" y2={a % 90 === 0 ? 26 : 20} stroke="#191919" strokeWidth="2"
                transform={`rotate(${a} 100 100)`} />
        ))}
        <motion.g initial={{ rotate: -90 }} animate={{ rotate: angle }}
                  transition={{ type: 'spring', stiffness: 60, damping: 11, delay: 0.2 }}
                  style={{ transformOrigin: '100px 100px', transformBox: 'view-box' }}>
          <line x1="100" y1="100" x2="100" y2="30" stroke="#191919" strokeWidth="5" strokeLinecap="round" />
        </motion.g>
        <circle cx="100" cy="100" r="9" fill="#191919" />
      </svg>
      <div className="mono -mt-1 flex justify-between text-[0.625rem] font-bold uppercase">
        <span>0</span><span>50</span><span>100</span>
      </div>
    </div>
  )
}

/**
 * Top of the result page: the verdict as one loud block of colour, the model
 * score on a dial, and the two downloads. Everything below it is the detailed
 * workbench.
 */
export default function VerdictHero({ result, meta, mediaLabel, reportUrl, onExportJSON, experimental }) {
  const slab = slabFor(meta.tone, meta.label)
  const score = typeof result.fake_probability === 'number' ? result.fake_probability : null

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.2, 0.9, 0.3, 1] }}
      className="relative mb-8 overflow-hidden rounded-2xl border-2 border-[#191919] text-[#191919]"
      style={{ background: slab.bg, boxShadow: '10px 10px 0 var(--pop)' }}
    >
      <div className="pointer-events-none absolute inset-0 opacity-25"
           style={{ backgroundImage: 'radial-gradient(#191919 1.2px, transparent 1.2px)', backgroundSize: '20px 20px' }}
           aria-hidden="true" />

      <div className="relative grid gap-8 p-6 sm:p-10 lg:grid-cols-[1.5fr_1fr] lg:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="sticker" style={{ '--r': '-3deg', background: '#191919', color: slab.bg, boxShadow: '3px 3px 0 #ececed' }}>
              {slab.sticker}
            </span>
            <span className="mono text-[0.75rem] font-bold uppercase">
              {mediaLabel}{result.case_reference ? ` · ${result.case_reference}` : ''}
            </span>
            {experimental && (
              <span className="mono rounded-sm border-2 border-[#191919] bg-[#ececed] px-2 py-0.5 text-[0.625rem] font-bold uppercase">
                Experimental
              </span>
            )}
          </div>

          <h2 className="wide mt-5 font-black uppercase"
              style={{ fontSize: 'clamp(2rem, 4.4vw, 4.5rem)', lineHeight: 0.9, letterSpacing: '-0.055em', hyphens: 'none', overflowWrap: 'normal' }}>
            {meta.label}
          </h2>

          <p className="mt-5 max-w-xl truncate text-[1rem] font-semibold" title={result.original_filename}>
            {result.original_filename}
          </p>

          <div className="mt-7 flex flex-wrap gap-3">
            <a href={reportUrl || `/api/jobs/${result.id}/report`} target="_blank" rel="noreferrer"
               className="btn btn-lg border-[#191919] bg-[#191919] uppercase text-[#ececed] shadow-[5px_5px_0_#ececed] hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-[8px_8px_0_#ececed]"
               style={{ fontStretch: '115%', fontWeight: 800 }}>
              <FileText size={16} /> PDF report
            </a>
            <button onClick={onExportJSON}
                    className="btn btn-lg border-[#191919] bg-transparent uppercase text-[#191919] hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-[#ececed] hover:shadow-[6px_6px_0_#191919]"
                    style={{ fontStretch: '115%', fontWeight: 800 }}>
              <Download size={16} /> JSON
            </button>
          </div>
        </div>

        {score !== null && (
          <div className="flex flex-col items-center rounded-xl border-2 border-[#191919] bg-[#ececed] p-5">
            <span className="mono text-[0.6875rem] font-bold uppercase tracking-wider">Model score</span>
            <span className="wide tnum mt-1 text-5xl font-black leading-none">{(score * 100).toFixed(1)}<span className="text-2xl">%</span></span>
            <div className="mt-3 w-full"><ScoreDial value={score} /></div>
            <p className="mt-3 text-center text-[0.75rem] leading-snug opacity-75">
              How strongly the detectors leaned toward manipulation. Read it with the evidence below, not on its own.
            </p>
          </div>
        )}
      </div>
    </motion.section>
  )
}
