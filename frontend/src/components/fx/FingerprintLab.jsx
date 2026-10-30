import { useEffect, useRef, useState } from 'react'

/**
 * Live SHA-256 playground. Whatever the visitor types is hashed in the browser
 * (Web Crypto) and drawn as a mirrored 16×16 pixel pattern plus a byte bar.
 * Changing one character flips about half of the 256 bits — the counter shows
 * the real number for each edit.
 */

const COLORS = ['#191919', '#23f871', '#57c690', '#43b6a1', '#a7e1c5', '#024219', '#ececed', '#19443c']

async function sha256(text) {
  const data = new TextEncoder().encode(text)
  const buf = await crypto.subtle.digest('SHA-256', data)
  return new Uint8Array(buf)
}

function bitDiff(a, b) {
  if (!a || !b) return null
  let n = 0
  for (let i = 0; i < a.length; i++) {
    let x = a[i] ^ b[i]
    while (x) { n += x & 1; x >>= 1 }
  }
  return n
}

/** 16 rows × 8 cells from the hash, mirrored to 16 columns. */
function cellsFrom(bytes) {
  const cells = []
  for (let r = 0; r < 16; r++) {
    const row = []
    for (let c = 0; c < 8; c++) {
      const idx = (r * 8 + c) % 32
      const v = bytes[idx] ^ bytes[(idx * 7 + r) % 32]
      row.push(v & 1 ? COLORS[(v >> 1) % COLORS.length] : null)
    }
    cells.push([...row, ...row.slice().reverse()])
  }
  return cells
}

export default function FingerprintLab() {
  const [text, setText] = useState('holiday-photo.jpg')
  const [bytes, setBytes] = useState(null)
  const [flipped, setFlipped] = useState(null)
  const prev = useRef(null)
  const supported = typeof crypto !== 'undefined' && Boolean(crypto.subtle)

  useEffect(() => {
    if (!supported) return undefined
    let live = true
    sha256(text).then((b) => {
      if (!live) return
      setFlipped(bitDiff(prev.current, b))
      prev.current = b
      setBytes(b)
    })
    return () => { live = false }
  }, [text, supported])

  const hex = bytes ? [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('') : ''
  const cells = bytes ? cellsFrom(bytes) : null

  return (
    <div className="grid gap-8 overflow-hidden rounded-2xl border-2 border-[#191919] p-6 sm:p-10 lg:grid-cols-[1.1fr_1fr] lg:items-center"
         style={{ background: 'var(--sea)', color: '#ececed', boxShadow: '10px 10px 0 #ececed' }}>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-3">
          <span className="sticker" style={{ '--r': '2deg' }}>Lab B</span>
          <span className="mono text-[0.75rem] font-bold uppercase" style={{ color: '#a7e1c5' }}>Fingerprint anything</span>
        </div>

        <h3 className="wide mt-6 font-black uppercase" style={{ fontSize: 'clamp(1.875rem, 3.6vw, 3.25rem)', lineHeight: 0.92, letterSpacing: '-0.05em' }}>
          Change one letter.<br /><span className="serif-i normal-case" style={{ color: 'var(--acid)' }}>Watch everything change.</span>
        </h3>
        <p className="mt-4 max-w-md text-[1rem] leading-relaxed" style={{ color: '#a7e1c5' }}>
          Every upload gets a SHA-256 fingerprint. Type below and your browser computes the real thing:
          the slightest edit gives a completely different pattern, which is how a report is tied to one exact file.
        </p>

        <label className="mono mt-7 block text-[0.6875rem] font-bold uppercase tracking-wider" htmlFor="fp-input" style={{ color: 'var(--acid)' }}>
          Type anything
        </label>
        <input id="fp-input" value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} maxLength={120}
               className="mt-2 w-full rounded-md border-2 border-[#191919] bg-[#ececed] px-4 py-3 text-[1.125rem] font-bold text-[#191919] outline-none transition-shadow focus:shadow-[5px_5px_0_var(--acid)]" />

        {supported ? (
          <>
            <p className="mono mt-4 break-all text-[0.75rem] leading-relaxed" style={{ color: '#a7e1c5' }} aria-label="SHA-256 hash">
              {hex.slice(0, 32)}<br />{hex.slice(32)}
            </p>
            <p className="mono mt-3 text-[0.8125rem] font-bold" aria-live="polite">
              {flipped === null
                ? 'Edit the text to see how many bits flip.'
                : <>Last edit flipped <span style={{ color: 'var(--acid)' }}>{flipped}</span> of 256 bits.</>}
            </p>
          </>
        ) : (
          <p className="mt-4 text-[0.875rem]" style={{ color: '#a7e1c5' }}>Your browser blocks Web Crypto on this connection, so the live hash is unavailable.</p>
        )}
      </div>

      {/* the pattern */}
      <div className="mx-auto w-full max-w-[22rem]" aria-hidden="true">
        <div className="grid aspect-square grid-cols-16 gap-[2px] rounded-xl border-2 border-[#191919] bg-[#191919] p-2"
             style={{ gridTemplateColumns: 'repeat(16, minmax(0, 1fr))' }}>
          {(cells || Array.from({ length: 16 }, () => Array(16).fill(null))).flat().map((c, i) => (
            <span key={i} className="rounded-[2px]"
                  style={{
                    background: c || '#28282b',
                    transform: c ? 'scale(1)' : 'scale(0.55)',
                    transition: `background .35s ${(i % 16) * 12}ms, transform .35s ${(i % 16) * 12}ms`,
                  }} />
          ))}
        </div>
        <div className="mt-3 flex h-8 overflow-hidden rounded-md border-2 border-[#191919]">
          {bytes && [...bytes].map((b, i) => (
            <span key={i} className="flex-1" style={{ background: COLORS[b % COLORS.length], transition: 'background .35s' }} />
          ))}
        </div>
      </div>
    </div>
  )
}
