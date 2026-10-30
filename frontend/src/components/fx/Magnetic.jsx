import { useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'

/** Wrapper that pulls its child a little toward the cursor, then springs back. */
export default function Magnetic({ children, strength = 0.35, className = '' }) {
  const ref = useRef(null)
  const x = useSpring(useMotionValue(0), { stiffness: 260, damping: 18, mass: 0.4 })
  const y = useSpring(useMotionValue(0), { stiffness: 260, damping: 18, mass: 0.4 })

  function onMove(e) {
    const rect = ref.current.getBoundingClientRect()
    x.set((e.clientX - (rect.left + rect.width / 2)) * strength)
    y.set((e.clientY - (rect.top + rect.height / 2)) * strength)
  }

  function onLeave() {
    x.set(0)
    y.set(0)
  }

  return (
    <motion.span ref={ref} onPointerMove={onMove} onPointerLeave={onLeave} style={{ x, y }}
                 className={`inline-block ${className}`}>
      {children}
    </motion.span>
  )
}
