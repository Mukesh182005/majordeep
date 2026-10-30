import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

/**
 * "Even text can be faked": letters in the sentence are quietly swapped for
 * look-alike characters from other scripts (Cyrillic а for Latin a, ...).
 * Nothing changes visibly until the visitor runs the scan, which marks every
 * impostor with its real code point. A toy demo of spoofing, not a product
 * feature, so it says so.
 *
 * The sentence is set in Arial: unlike the brand fonts it carries Cyrillic,
 * so the look-alikes render with identical shapes.
 */

const SENTENCE = 'Seeing is no longer believing. Scan everything.'

const LOOKALIKES = {
  a: ['а', 'CYRILLIC SMALL A'],
  e: ['е', 'CYRILLIC SMALL IE'],
  o: ['о', 'CYRILLIC SMALL O'],
  p: ['р', 'CYRILLIC SMALL ER'],
  c: ['с', 'CYRILLIC SMALL ES'],
  i: ['і', 'CYRILLIC SMALL I'],
  s: ['ѕ', 'CYRILLIC SMALL DZE'],
  y: ['у', 'CYRILLIC SMALL U'],
  S: ['Ѕ', 'CYRILLIC CAPITAL DZE'],
}

const SWAPPABLE = [...SENTENCE].map((ch, i) => (LOOKALIKES[ch] ? i : -1)).filter((i) => i >= 0)
const MAX_FAKES = 7

// Character indices grouped into words (trailing space kept), so a line
// only ever breaks between words.
const WORDS = SENTENCE.split(/(?<= )/).reduce((acc, word) => {
  const start = acc.length ? acc[acc.length - 1].at(-1) + 1 : 0
  acc.push([...word].map((_, k) => start + k))
  return acc
}, [])

function pickFakes(prev) {
  // Drift: keep most of the current impostors, swap one or two.
  const next = new Set(prev)
  const pool = SWAPPABLE.filter((i) => !next.has(i))
  if (next.size >= MAX_FAKES) next.delete([...next][Math.floor(Math.random() * next.size)])
  if (pool.length) next.add(pool[Math.floor(Math.random() * pool.length)])
  return next
}

export default function HomoglyphLab() {
  const [fakes, setFakes] = useState(() => {
    let s = new Set()
    for (let k = 0; k < 5; k++) s = pickFakes(s)
    return s
  })
  const [scanned, setScanned] = useState(false)
  const [sweep, setSweep] = useState(0)
  const timer = useRef(0)

  useEffect(() => {
    if (scanned || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    timer.current = window.setInterval(() => setFakes((f) => pickFakes(f)), 1400)
    return () => window.clearInterval(timer.current)
  }, [scanned])

  function toggle() {
    setScanned((v) => !v)
    setSweep((n) => n + 1)
  }

  const chars = [...SENTENCE]
  // Flagged letters close to the previous flagged one drop their tag to a
  // second row so neighbouring tags never overlap.
  const tagRow = new Map()
  let last = -99
  let lastRow = false
  for (const i of [...fakes].sort((a, b) => a - b)) {
    const row = i - last < 4 ? !lastRow : false
    tagRow.set(i, row)
    last = i
    lastRow = row
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border-2 border-[#191919] p-6 sm:p-10"
         style={{ background: '#ececed', color: '#191919', boxShadow: '10px 10px 0 var(--acid)' }}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="sticker" style={{ '--r': '-3deg', background: '#191919', color: 'var(--acid)', boxShadow: '3px 3px 0 var(--acid)' }}>
            Lab A
          </span>
          <span className="mono text-[0.75rem] font-bold uppercase">Even text can be faked</span>
        </div>
        <span className="mono text-[0.6875rem] uppercase opacity-60">Toy demo · look-alike characters</span>
      </div>

      <p className="relative mt-8 select-text"
         style={{ fontFamily: '"Arial Black", Arial, Helvetica, sans-serif', fontWeight: 900, fontSize: 'clamp(1.75rem, 4.6vw, 4.25rem)', lineHeight: 1.08, letterSpacing: '-0.03em' }}
         aria-label={SENTENCE}>
        {/* the sweep bar that runs across when a scan starts */}
        {scanned && (
          <motion.span key={sweep} aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 w-24"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(35,248,113,.55), transparent)' }}
            initial={{ left: '-10%' }} animate={{ left: '110%' }} transition={{ duration: 0.9, ease: 'easeInOut' }} />
        )}
        {WORDS.map((w) => (
          <span key={w[0]} className="inline-block whitespace-nowrap">
            {w.map((i) => {
              const ch = chars[i]
              const fake = fakes.has(i)
              const shown = fake ? LOOKALIKES[ch][0] : ch
              const flagged = scanned && fake
              return (
                <span key={i} aria-hidden="true" className="relative inline-block whitespace-pre"
                      style={{ color: flagged ? '#ff4d3d' : 'inherit', transition: `color .2s ${flagged ? i * 0.012 : 0}s` }}>
                  {shown}
                  {flagged && (
                    <motion.span initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: 0.3 + i * 0.012, duration: 0.25 }}
                      className="absolute inset-x-0 -bottom-1 h-[0.12em] origin-left" style={{ background: '#ff4d3d' }} />
                  )}
                  {flagged && (
                    <motion.span initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 + i * 0.012 }}
                      className={`mono absolute left-1/2 top-full z-10 hidden -translate-x-1/2 whitespace-nowrap sm:block rounded-sm border-2 border-[#191919] px-1 text-[0.5625rem] font-bold leading-tight sm:text-[0.625rem] ${tagRow.get(i) ? 'mt-7' : 'mt-2'}`}
                      style={{ background: '#ff4d3d', color: '#191919', letterSpacing: 0 }}>
                      U+{shown.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')}
                    </motion.span>
                  )}
                </span>
              )
            })}
          </span>
        ))}
      </p>

      <div className={`flex flex-wrap items-center gap-4 ${scanned ? 'mt-8 sm:mt-20' : 'mt-8'}`}>
        <button onClick={toggle}
                className="btn btn-lg border-[#191919] uppercase shadow-[5px_5px_0_#191919] hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-[8px_8px_0_#191919] active:translate-x-1 active:translate-y-1 active:shadow-none"
                style={{ background: scanned ? '#191919' : 'var(--acid)', color: scanned ? 'var(--acid)' : '#191919', fontStretch: '115%', fontWeight: 800 }}>
          {scanned ? 'Reset' : 'Scan text'}
        </button>
        <p className="text-[0.9375rem] font-semibold" aria-live="polite">
          {scanned
            ? <><span style={{ color: '#ff4d3d' }}>{fakes.size} of {chars.length}</span> characters are impostors: {
                [...fakes].sort((a, b) => a - b).map((i) => LOOKALIKES[chars[i]][1]).filter((v, k, a) => a.indexOf(v) === k).slice(0, 3).join(', ')
              }{fakes.size > 3 ? '…' : ''}</>
            : 'This sentence is being tampered with right now. Can you see where?'}
        </p>
      </div>
    </div>
  )
}
