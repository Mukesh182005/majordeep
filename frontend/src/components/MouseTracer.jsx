import { useEffect, useRef } from 'react'

/**
 * MouseTracer Component
 *
 * Renders a lightweight, high-performance canvas mouse trail that smoothly
 * interpolates from red (at the cursor head) to green (at the fading tail)
 * with graceful opacity dissipation.
 */
export default function MouseTracer() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    let animationFrameId
    let points = []
    let mouseMoved = false

    // Resize canvas to full viewport
    const handleResize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    handleResize()
    window.addEventListener('resize', handleResize)

    // Add points on mouse movement
    const handleMouseMove = (e) => {
      mouseMoved = true
      points.push({
        x: e.clientX,
        y: e.clientY,
        time: performance.now(),
      })
    }
    window.addEventListener('mousemove', handleMouseMove, { passive: true })

    // Optional touch support
    const handleTouchMove = (e) => {
      if (e.touches && e.touches[0]) {
        mouseMoved = true
        points.push({
          x: e.touches[0].clientX,
          y: e.touches[0].clientY,
          time: performance.now(),
        })
      }
    }
    window.addEventListener('touchmove', handleTouchMove, { passive: true })

    const TRAIL_DURATION_MS = 450 // trail lifespan

    // Interpolates from Red (rgb(239, 68, 68)) at t=0 to Green (rgb(16, 185, 129)) at t=1
    const getTracerColor = (t, alpha) => {
      const r = Math.round(239 + (16 - 239) * t)
      const g = Math.round(68 + (185 - 68) * t)
      const b = Math.round(68 + (129 - 68) * t)
      return `rgba(${r}, ${g}, ${b}, ${Math.max(0, Math.min(1, alpha))})`
    }

    // Animation render loop
    const render = () => {
      const now = performance.now()

      // Prune points that have exceeded lifespan
      points = points.filter((p) => now - p.time < TRAIL_DURATION_MS)

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      if (points.length > 1) {
        // Draw trailing segments
        for (let i = 0; i < points.length - 1; i++) {
          const p1 = points[i]
          const p2 = points[i + 1]

          // Progress from tail (t=1, green) to head (t=0, red)
          // index 0 is oldest (tail), index length-1 is newest (head)
          const normIdx = i / (points.length - 1) // 0 at tail, 1 at head
          const t = 1 - normIdx // 1 at tail (green), 0 at head (red)

          const age = (now - p2.time) / TRAIL_DURATION_MS
          const alpha = (1 - age) * 0.75
          const width = 2 + (1 - t) * 4.5 // thicker at cursor head, thinner at tail

          ctx.beginPath()
          ctx.moveTo(p1.x, p1.y)
          ctx.lineTo(p2.x, p2.y)
          ctx.strokeStyle = getTracerColor(t, alpha)
          ctx.lineWidth = width
          ctx.lineCap = 'round'
          ctx.lineJoin = 'round'
          ctx.stroke()
        }

        // Draw soft glowing head dot at newest point
        const head = points[points.length - 1]
        const headAge = (now - head.time) / TRAIL_DURATION_MS
        const headAlpha = (1 - headAge) * 0.9

        ctx.beginPath()
        ctx.arc(head.x, head.y, 4, 0, Math.PI * 2)
        ctx.fillStyle = getTracerColor(0, headAlpha) // Pure red head
        ctx.fill()
      }

      animationFrameId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('touchmove', handleTouchMove)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-50 overflow-hidden"
      style={{
        pointerEvents: 'none',
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 9999,
      }}
      aria-hidden="true"
    />
  )
}
