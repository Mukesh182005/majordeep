import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'

/**
 * A statement whose words light up one by one as it scrolls through the
 * viewport. Highlighted words turn acid. Screen readers get the plain text.
 */

const TEXT = 'Deepfakes are cheap. Doubt is cheaper. So we built a detector that *shows its work,* says when it is *not sure,* and *forgets your files* the moment you ask.'

function Word({ word, range, progress, accent }) {
  const opacity = useTransform(progress, range, [0.12, 1])
  const y = useTransform(progress, range, [8, 0])
  return (
    <motion.span style={{ opacity, y }} className={`mr-[0.25em] inline-block ${accent ? 'serif-i normal-case text-gradient' : ''}`}>
      {word}
    </motion.span>
  )
}

export default function Manifesto() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.85', 'end 0.45'] })

  // Words wrapped in *…* are accented.
  let accent = false
  const words = TEXT.split(' ').map((raw) => {
    const starts = raw.startsWith('*')
    const ends = raw.endsWith('*') || raw.endsWith('*,')
    if (starts) accent = true
    const w = { text: raw.replace(/\*/g, ''), accent }
    if (ends) accent = false
    return w
  })

  return (
    <section ref={ref} className="py-24 lg:py-36">
      <span className="eyebrow">Why this exists</span>
      <p className="wide mt-6 font-black uppercase leading-[0.98]" aria-label={TEXT.replace(/\*/g, '')}
         style={{ fontSize: 'clamp(2rem, 5.2vw, 5rem)', letterSpacing: '-0.05em' }}>
        <span aria-hidden="true">
          {words.map((w, i) => (
            <Word key={i} word={w.text} accent={w.accent} progress={scrollYProgress}
                  range={[i / words.length, Math.min(1, (i + 1.5) / words.length)]} />
          ))}
        </span>
      </p>
    </section>
  )
}
