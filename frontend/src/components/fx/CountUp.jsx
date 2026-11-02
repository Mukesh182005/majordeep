import { useEffect, useState } from 'react'

/**
 * Counts a number up from 0 to its value once, keeping the text around it
 * ("76.0%", "88"). Screen readers and anything that cannot be parsed get the
 * final text straight away; reduced-motion users see no counting.
 */
export default function CountUp({ value, duration = 900 }) {
  const text = String(value ?? '')
  const match = text.match(/^(\D*)(\d+(?:\.\d+)?)(.*)$/)
  const target = match ? Number(match[2]) : null
  const decimals = match && match[2].includes('.') ? match[2].split('.')[1].length : 0
  const [shown, setShown] = useState(target === null ? text : `${match[1]}${(0).toFixed(decimals)}${match[3]}`)

  useEffect(() => {
    if (target === null) { setShown(text); return undefined }
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reduce || typeof requestAnimationFrame !== 'function') { setShown(text); return undefined }
    let raf = 0
    const start = performance.now()
    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(p < 1 ? `${match[1]}${(target * eased).toFixed(decimals)}${match[3]}` : text)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])

  return (
    <span className="tnum" aria-label={text}>
      <span aria-hidden="true">{shown}</span>
    </span>
  )
}
