import { useEffect, useRef, useState } from 'react'

const GLYPHS = '!<>-_\\/[]{}=+*^?#01ABCDEF'

/**
 * Text that "decodes" from random glyphs: once when it scrolls into view,
 * and again on hover. Screen readers always get the real text via aria-label.
 */
export default function Scramble({ text, className = '', as: Tag = 'span' }) {
  const [shown, setShown] = useState(text)
  const ref = useRef(null)
  const raf = useRef(0)

  function run() {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    cancelAnimationFrame(raf.current)
    const start = performance.now()
    const duration = 500 + text.length * 18
    const step = (now) => {
      const p = Math.min(1, (now - start) / duration)
      const settled = Math.floor(p * text.length)
      let out = ''
      for (let i = 0; i < text.length; i++) {
        out += i < settled || text[i] === ' ' ? text[i] : GLYPHS[(Math.random() * GLYPHS.length) | 0]
      }
      setShown(out)
      if (p < 1) raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
  }

  useEffect(() => {
    setShown(text)
    const el = ref.current
    if (!el || typeof IntersectionObserver === 'undefined') return undefined
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        run()
        io.disconnect()
      }
    }, { threshold: 0.6 })
    io.observe(el)
    return () => {
      io.disconnect()
      cancelAnimationFrame(raf.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])

  return (
    <Tag ref={ref} className={className} onPointerEnter={run} aria-label={text}>
      <span aria-hidden="true">{shown}</span>
    </Tag>
  )
}
