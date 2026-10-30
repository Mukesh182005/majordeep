import { useEffect, useRef } from 'react'

/**
 * Hero canvas: a dot-matrix portrait that a scan beam sweeps over. The cursor
 * is a loupe — inside it, dots switch to heatmap colours and jitter, and the
 * "seam" dots along the jaw and eyes light up. Purely decorative (aria-hidden);
 * with prefers-reduced-motion it draws one still frame.
 */

const ACID = [35, 248, 113]
const TEAL = [67, 182, 161]
const PINE = [87, 198, 144]
const SIGNAL = [255, 77, 61]
const AMBER = [255, 176, 32]

function mix(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]
}

/** Rasterises a head-and-shoulders silhouette into a list of dots. */
function buildDots(w, h) {
  const off = document.createElement('canvas')
  off.width = w
  off.height = h
  const g = off.getContext('2d')
  const cx = w / 2
  const s = Math.min(w, h * 0.82)

  g.fillStyle = '#fff'
  // head
  g.beginPath()
  g.ellipse(cx, h * 0.38, s * 0.22, s * 0.29, 0, 0, Math.PI * 2)
  g.fill()
  // neck
  g.fillRect(cx - s * 0.085, h * 0.58, s * 0.17, h * 0.14)
  // shoulders
  g.beginPath()
  g.ellipse(cx, h * 1.02, s * 0.52, h * 0.3, 0, Math.PI, Math.PI * 2)
  g.fill()

  // features punched out so the face reads
  g.globalCompositeOperation = 'destination-out'
  for (const dx of [-1, 1]) {
    g.beginPath()
    g.ellipse(cx + dx * s * 0.085, h * 0.35, s * 0.045, s * 0.018, 0, 0, Math.PI * 2)
    g.fill()
  }
  g.beginPath()
  g.ellipse(cx, h * 0.5, s * 0.07, s * 0.012, 0, 0, Math.PI * 2)
  g.fill()

  const data = g.getImageData(0, 0, w, h).data
  const step = Math.max(6, Math.round(Math.min(w, h) / 70))
  const dots = []
  for (let y = step / 2; y < h; y += step) {
    for (let x = step / 2; x < w; x += step) {
      const inside = data[(Math.floor(y) * w + Math.floor(x)) * 4 + 3] > 0
      // A sparse field of background dots keeps the frame from feeling empty.
      if (!inside && Math.random() > 0.08) continue
      // "Seams": a jawline arc and a ring around the eyes — where a face swap blends.
      const jx = (x - cx) / (s * 0.22)
      const jy = (y - h * 0.38) / (s * 0.29)
      const r = Math.hypot(jx, jy)
      const jaw = inside && jy > 0.35 && r > 0.82 && r < 1.0
      const eye = inside && Math.abs(y - h * 0.35) < s * 0.05 && Math.abs(Math.abs(x - cx) - s * 0.085) < s * 0.08
      dots.push({
        x, y, inside,
        seam: jaw || eye,
        phase: Math.random() * Math.PI * 2,
        size: inside ? 1.7 + Math.random() * 0.7 : 0.9,
      })
    }
  }
  return { dots, step }
}

export default function ScanField({ className = '' }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx || typeof ResizeObserver === 'undefined' || typeof IntersectionObserver === 'undefined') return

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let w = 0
    let h = 0
    let field = { dots: [] }
    let raf = 0
    let running = false
    let visible = true
    const pointer = { x: -9999, y: -9999, tx: -9999, ty: -9999, active: false }
    const start = performance.now()

    function resize() {
      const rect = canvas.getBoundingClientRect()
      w = Math.max(1, Math.round(rect.width))
      h = Math.max(1, Math.round(rect.height))
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      field = buildDots(w, h)
      if (!running) draw(performance.now())
    }

    function draw(now) {
      const t = (now - start) / 1000
      ctx.clearRect(0, 0, w, h)

      // ease the loupe toward the pointer; idle, it drifts over the face on its own
      if (!pointer.active) {
        pointer.tx = w / 2 + Math.cos(t * 0.55) * w * 0.16
        pointer.ty = h * 0.42 + Math.sin(t * 0.8) * h * 0.12
      }
      pointer.x += (pointer.tx - pointer.x) * 0.12
      pointer.y += (pointer.ty - pointer.y) * 0.12
      if (pointer.x < -1000) { pointer.x = pointer.tx; pointer.y = pointer.ty }

      const beamY = reduce ? h * 0.45 : ((t * 0.22) % 1.25) * h - h * 0.1
      const loupeR = Math.min(w, h) * 0.2

      for (const d of field.dots) {
        const breathe = reduce ? 0 : Math.sin(t * 1.4 + d.phase) * 0.35
        const dl = Math.hypot(d.x - pointer.x, d.y - pointer.y)
        const inLoupe = dl < loupeR
        const beam = Math.max(0, 1 - Math.abs(d.y - beamY) / 26)

        let x = d.x
        let y = d.y + breathe
        let color
        let alpha
        let size = d.size

        if (inLoupe && d.inside) {
          const k = 1 - dl / loupeR
          if (d.seam) {
            color = mix(AMBER, SIGNAL, 0.5 + 0.5 * Math.sin(t * 6 + d.phase))
            alpha = 0.95
            size += 1.2 * k + 0.6
            if (!reduce) x += Math.sin(t * 30 + d.phase) * 1.4 * k
          } else {
            color = mix(PINE, ACID, k)
            alpha = 0.35 + 0.35 * k
          }
        } else if (d.inside) {
          // a soft top-lit gradient so the head reads as a form, not a flat stencil
          const lit = 1 - d.y / h
          color = mix(TEAL, ACID, Math.min(1, beam * 1.4 + lit * 0.55))
          alpha = 0.42 + lit * 0.3 + beam * 0.5
          size += beam * 0.9
        } else {
          color = TEAL
          alpha = 0.12 + beam * 0.3
        }

        ctx.fillStyle = `rgba(${color[0] | 0},${color[1] | 0},${color[2] | 0},${alpha})`
        ctx.fillRect(x - size / 2, y - size / 2, size, size)
      }

      // scan beam
      const grad = ctx.createLinearGradient(0, beamY - 40, 0, beamY + 2)
      grad.addColorStop(0, 'rgba(35,248,113,0)')
      grad.addColorStop(1, 'rgba(35,248,113,0.18)')
      ctx.fillStyle = grad
      ctx.fillRect(0, beamY - 40, w, 42)
      ctx.fillStyle = 'rgba(35,248,113,0.85)'
      ctx.fillRect(0, beamY, w, 1)

      // loupe ring + ticks + label
      ctx.save()
      ctx.strokeStyle = 'rgba(35,248,113,0.95)'
      ctx.lineWidth = 2
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.arc(pointer.x, pointer.y, loupeR, 0, Math.PI * 2)
      ctx.stroke()
      ctx.strokeStyle = 'rgba(255,77,61,0.85)'
      ctx.setLineDash([2, 6])
      ctx.beginPath()
      ctx.arc(pointer.x, pointer.y, loupeR + 8, reduce ? 0 : t * 0.6, (reduce ? 0 : t * 0.6) + Math.PI * 1.2)
      ctx.stroke()
      ctx.setLineDash([])
      for (let i = 0; i < 4; i++) {
        const a = (i * Math.PI) / 2
        ctx.beginPath()
        ctx.moveTo(pointer.x + Math.cos(a) * (loupeR - 6), pointer.y + Math.sin(a) * (loupeR - 6))
        ctx.lineTo(pointer.x + Math.cos(a) * (loupeR + 4), pointer.y + Math.sin(a) * (loupeR + 4))
        ctx.stroke()
      }
      ctx.font = '700 11px "Space Mono", ui-monospace, monospace'
      ctx.fillStyle = 'rgba(35,248,113,1)'
      ctx.fillText('LOUPE · SEAM CHECK', pointer.x - loupeR, pointer.y - loupeR - 14)
      ctx.restore()
    }

    function loop(now) {
      draw(now)
      raf = requestAnimationFrame(loop)
    }

    function play() {
      if (reduce || running || !visible || document.hidden) return
      running = true
      raf = requestAnimationFrame(loop)
    }

    function pause() {
      running = false
      cancelAnimationFrame(raf)
    }

    function onMove(e) {
      const rect = canvas.getBoundingClientRect()
      pointer.tx = e.clientX - rect.left
      pointer.ty = e.clientY - rect.top
      pointer.active = true
      if (reduce) draw(performance.now())
    }

    function onLeave() {
      pointer.active = false
    }

    function onVisibility() {
      if (document.hidden) pause()
      else play()
    }

    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
      if (visible) play()
      else pause()
    })
    io.observe(canvas)
    canvas.addEventListener('pointermove', onMove)
    canvas.addEventListener('pointerleave', onLeave)
    document.addEventListener('visibilitychange', onVisibility)

    resize()
    play()

    return () => {
      pause()
      ro.disconnect()
      io.disconnect()
      canvas.removeEventListener('pointermove', onMove)
      canvas.removeEventListener('pointerleave', onLeave)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  return <canvas ref={canvasRef} className={`block h-full w-full ${className}`} aria-hidden="true" />
}
