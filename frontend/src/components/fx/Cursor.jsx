import { useEffect, useRef } from 'react'

const HOT = 'a, button, [role="button"], input, select, textarea, label, [data-cursor="hot"]'

/**
 * Lagging ring that follows the pointer and swells over clickable things.
 * Mouse and pen only (hidden on touch by CSS), skipped for reduced motion.
 * Moves via a transform in a rAF loop, so there are no React re-renders.
 */
export default function Cursor() {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.style.display = 'none'
      return
    }

    const target = { x: -100, y: -100 }
    const pos = { x: -100, y: -100 }
    let raf = 0

    function onMove(e) {
      target.x = e.clientX
      target.y = e.clientY
      el.classList.toggle('is-hot', Boolean(e.target.closest?.(HOT)))
    }

    function onLeave() {
      target.x = -100
      target.y = -100
    }

    function tick() {
      pos.x += (target.x - pos.x) * 0.22
      pos.y += (target.y - pos.y) * 0.22
      el.style.transform = `translate3d(${pos.x}px, ${pos.y}px, 0)`
      raf = requestAnimationFrame(tick)
    }

    window.addEventListener('pointermove', onMove)
    document.documentElement.addEventListener('pointerleave', onLeave)
    raf = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('pointermove', onMove)
      document.documentElement.removeEventListener('pointerleave', onLeave)
    }
  }, [])

  return <div ref={ref} className="cursor-ring" aria-hidden="true" />
}
