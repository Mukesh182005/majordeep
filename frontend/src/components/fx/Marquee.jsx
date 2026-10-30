/**
 * Endless ticker tape. The list is rendered twice and the track slides by half
 * its width, so the loop has no seam. `tone` picks the band colour, `tilt`
 * rotates the whole band. Decorative: screen readers get the list once.
 */
const TONES = {
  acid: { background: 'var(--acid)', color: '#191919' },
  mint: { background: 'var(--mint)', color: '#191919' },
  ink: { background: '#191919', color: 'var(--acid)' },
}

export default function Marquee({ items, tone = 'acid', tilt = 0, reverse = false, className = '' }) {
  const row = (hidden) => (
    <ul className="flex shrink-0 items-center" aria-hidden={hidden || undefined}>
      {items.map((item, i) => (
        <li key={i} className="flex items-center whitespace-nowrap">
          <span className="wide font-black uppercase" style={{ fontSize: 'clamp(1.25rem, 2.6vw, 2.25rem)', letterSpacing: '-0.03em' }}>
            {item}
          </span>
          <span className="mx-5 text-[1.5rem] sm:mx-8" aria-hidden="true">✺</span>
        </li>
      ))}
    </ul>
  )

  return (
    <div className={`marquee relative overflow-hidden border-y-2 py-3 sm:py-4 ${className}`}
         style={{ ...TONES[tone], borderColor: '#191919', transform: `rotate(${tilt}deg)` }}>
      <div className={`marquee-track flex w-max ${reverse ? 'reverse' : ''}`}>
        {row(false)}
        {row(true)}
      </div>
    </div>
  )
}
