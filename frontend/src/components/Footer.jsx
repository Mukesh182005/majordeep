import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../lib/api'
import { useAuth } from '../lib/useAuth'
import Marquee from './fx/Marquee'
import Magnetic from './fx/Magnetic'
import { ArrowRight, ChevronUp, Image as ImageIcon, Video as VideoIcon, Waveform } from './ui/Icons'

/**
 * Site footer: a call-to-action band, a live status panel read from
 * /api/health, the sitemap, a ticker and the wordmark.
 */

const LEARN = [
  ['The problem', '/how-it-works#problem'],
  ['Architecture', '/how-it-works#architecture'],
  ['Journey of a file', '/how-it-works#journey'],
  ['Inside the pipelines', '/how-it-works#pipelines'],
  ['How well it works', '/how-it-works#results'],
  ['Known limits', '/how-it-works#limits'],
  ['Glossary', '/how-it-works#glossary'],
]

const MODEL_ICON = { image: ImageIcon, audio: Waveform, video: VideoIcon }

function StatusPanel() {
  const [health, setHealth] = useState(undefined) // undefined = loading, null = offline
  const [open, setOpen] = useState(null)

  useEffect(() => {
    let live = true
    api.health().then((h) => live && setHealth(h)).catch(() => live && setHealth(null))
    return () => { live = false }
  }, [])

  const online = health && health.status === 'ok'
  return (
    <div className="self-start rounded-xl border-2 border-[#191919] p-5" style={{ background: "#191919", boxShadow: "6px 6px 0 var(--acid)" }}>
      <div className="flex items-center justify-between">
        <span className="mono text-[0.6875rem] font-bold uppercase text-[#a7a7ab]">System status · live</span>
        <span className="mono flex items-center gap-2 text-[0.75rem] font-bold uppercase"
              style={{ color: health === undefined ? '#a7a7ab' : online ? 'var(--acid)' : '#ff4d3d' }}>
          <span className={`h-2.5 w-2.5 rounded-full ${online ? 'animate-pulse' : ''}`}
                style={{ background: health === undefined ? '#56565c' : online ? 'var(--acid)' : '#ff4d3d' }} />
          {health === undefined ? 'Checking…' : online ? 'Online' : 'Offline'}
        </span>
      </div>

      {online ? (
        <>
          <div className="mono mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[0.6875rem] text-[#8a8a92]">
            <span>v{health.version}</span>
            <span>queue: {health.queue_enabled ? 'Celery + Redis' : 'inline'}</span>
          </div>
          <ul className="mt-4 space-y-2">
            {Object.entries(health.models || {}).map(([k, desc]) => {
              const Icon = MODEL_ICON[k] || ImageIcon
              return (
                <li key={k}>
                  <button onClick={() => setOpen(open === k ? null : k)} aria-expanded={open === k}
                          className="flex w-full items-start gap-3 rounded-md border-2 border-[#333337] p-2.5 text-left text-[#ececed] transition-colors hover:border-[var(--acid)]">
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-sm bg-[var(--acid)] text-[#191919]"><Icon size={14} /></span>
                    <span className="min-w-0">
                      <span className="mono block text-[0.6875rem] font-bold uppercase text-[var(--acid)]">{k}</span>
                      <span className={`block text-[0.75rem] leading-snug text-[#a7e1c5] ${open === k ? '' : 'truncate'}`}>{desc}</span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </>
      ) : (
        <p className="mt-3 text-[0.8125rem] text-[#8a8a92]">
          {health === undefined ? 'Asking the API which models it is serving…' : 'The API is not reachable right now, so analyses cannot run.'}
        </p>
      )}
    </div>
  )
}

export default function Footer() {
  const { user } = useAuth()
  // The landing page ends with its own call to action; skip the band there.
  const showCta = useLocation().pathname !== '/'

  return (
    <footer className="relative mt-16" style={{ color: '#ececed' }}>
      {/* ── CTA band ── */}
      {showCta && <div className="relative overflow-hidden border-y-2 border-[#191919]" style={{ background: 'var(--acid)', color: '#191919' }}>
        <div className="pointer-events-none absolute inset-0 opacity-25"
             style={{ backgroundImage: 'radial-gradient(#191919 1.2px, transparent 1.2px)', backgroundSize: '18px 18px' }} aria-hidden="true" />
        <div className="relative mx-auto flex max-w-content flex-col items-start justify-between gap-6 px-4 py-12 sm:px-6 md:flex-row md:items-center lg:px-10">
          <h2 className="wide font-black uppercase" style={{ fontSize: 'clamp(2rem, 5vw, 4.25rem)', lineHeight: 0.9, letterSpacing: '-0.055em' }}>
            Seen something<br /><span className="serif-i normal-case">fishy?</span>
          </h2>
          <div className="flex flex-wrap gap-3">
            <Magnetic>
              <Link to="/analyse" className="btn btn-lg group border-[#191919] bg-[#191919] uppercase text-[var(--acid)] shadow-[6px_6px_0_#ececed] hover:-translate-x-1 hover:-translate-y-1"
                    style={{ fontStretch: '115%', fontWeight: 800 }}>
                Scan it now <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
              </Link>
            </Magnetic>
            <Link to="/how-it-works" className="btn btn-lg border-[#191919] uppercase text-[#191919] hover:bg-[#ececed]"
                  style={{ fontStretch: '115%', fontWeight: 800 }}>
              How it works
            </Link>
          </div>
        </div>
      </div>}

      <Marquee items={['Image', 'Audio', 'Video', 'SHA-256', 'Inconclusive is an answer', 'Delete any scan', 'Look closer']} tone="ink" />

      {/* ── main grid ── */}
      <div style={{ background: 'var(--pine)' }}>
        <div className="mx-auto grid max-w-content gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[0.95fr_2.5fr_1.15fr] lg:px-10">
          <div>
            <Link to="/" className="group inline-flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-md border-2 border-[#191919] transition-transform group-hover:-rotate-6"
                    style={{ background: 'var(--acid)', boxShadow: '3px 3px 0 #ececed' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#191919" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M12 2.5 20 6v6c0 5-3.4 8.4-8 9.5C7.4 20.4 4 17 4 12V6z" />
                  <path d="M7.5 12.2c1.2-2 2.7-3 4.5-3s3.3 1 4.5 3c-1.2 2-2.7 3-4.5 3s-3.3-1-4.5-3z" />
                  <circle cx="12" cy="12.2" r="1.3" fill="#191919" />
                </svg>
              </span>
              <span className="wide text-xl font-black tracking-tight">DeepSentinel</span>
            </Link>
            <p className="mt-5 text-[0.9375rem] font-bold">Automated assessment only. Not forensic or legal evidence.</p>
            <p className="mt-2 text-[0.875rem] leading-relaxed text-[#a7e1c5]">
              Detection models make mistakes in both directions: real media can be flagged and manipulated
              media can pass. Treat every result as a lead to check, not a conclusion.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {['React', 'FastAPI', 'PyTorch', 'Celery', 'Postgres', 'Docker'].map((t) => (
                <span key={t} className="mono rounded-sm border-2 border-[#246a48] px-2 py-0.5 text-[0.625rem] font-bold uppercase text-[#a7e1c5]">{t}</span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          <nav aria-label="Product">
            <p className="mono mb-4 text-[0.75rem] font-bold uppercase tracking-wider text-[var(--acid)]">Product</p>
            <ul className="space-y-2.5 text-[0.9375rem]">
              <li><Link to="/analyse" className="footer-link">Analyse media</Link></li>
              {user
                ? <li><Link to="/history" className="footer-link">Scan history</Link></li>
                : <li><Link to="/login" className="footer-link">Sign in / register</Link></li>}
              <li><Link to="/how-it-works" className="footer-link">How it works</Link></li>
            </ul>
          </nav>

          <nav aria-label="Learn">
            <p className="mono mb-4 text-[0.75rem] font-bold uppercase tracking-wider text-[var(--acid)]">Learn</p>
            <ul className="space-y-2.5 text-[0.9375rem]">
              {LEARN.map(([label, to]) => <li key={to}><Link to={to} className="footer-link">{label}</Link></li>)}
            </ul>
          </nav>

          <nav aria-label="References">
            <p className="mono mb-4 text-[0.75rem] font-bold uppercase tracking-wider text-[var(--acid)]">References</p>
            <ul className="space-y-2.5 text-[0.9375rem]">
              <li><a href="https://huggingface.co/Sadanie/pellav2-audio-deepfake-detector" target="_blank" rel="noreferrer" className="footer-link">pellav2 (audio)</a></li>
              <li><a href="https://huggingface.co/yermandy/GenD_CLIP_L_14" target="_blank" rel="noreferrer" className="footer-link">GenD (video)</a></li>
              <li><a href="https://huggingface.co/OwensLab/commfor-model-384" target="_blank" rel="noreferrer" className="footer-link">Community Forensics</a></li>
              <li><a href="https://doi.org/10.7488/ds/2555" target="_blank" rel="noreferrer" className="footer-link">ASVspoof 2019 LA</a></li>
              <li><a href="https://doi.org/10.5281/zenodo.10066460" target="_blank" rel="noreferrer" className="footer-link">Synthbuster</a></li>
              <li><Link to="/references" className="footer-link font-bold text-[var(--acid)]">All references →</Link></li>
            </ul>
          </nav>

          <nav aria-label="Trust">
            <p className="mono mb-4 text-[0.75rem] font-bold uppercase tracking-wider text-[var(--acid)]">Trust</p>
            <ul className="space-y-2.5 text-[0.9375rem]">
              <li><Link to="/privacy" className="footer-link">Privacy &amp; retention</Link></li>
              <li><Link to="/how-it-works#security" className="footer-link">Security</Link></li>
              <li><Link to="/how-it-works#rejected" className="footer-link">What we got wrong</Link></li>
            </ul>
            <p className="mt-5 text-[0.8125rem] leading-relaxed text-[#a7e1c5]">
              Analyse only media you own or are authorised to analyse.
            </p>
          </nav>
          </div>

          <StatusPanel />
        </div>

        <div className="mx-auto max-w-content px-4 sm:px-6 lg:px-10">
          <div className="mono flex flex-wrap items-center justify-between gap-3 border-t-2 py-6 text-[0.75rem] uppercase tracking-wider text-[#a7e1c5]"
               style={{ borderColor: 'var(--sea)' }}>
            <span>© {new Date().getFullYear()} DeepSentinel · MIT licence</span>
            <span className="hidden sm:inline">Every number on this site cites its source file</span>
            <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                    className="group flex items-center gap-2 rounded-md border-2 border-[#246a48] px-3 py-1.5 font-bold transition-all hover:-translate-y-1 hover:border-[var(--acid)] hover:text-[var(--acid)]">
              Back to top <ChevronUp size={14} className="transition-transform group-hover:-translate-y-0.5" />
            </button>
          </div>
        </div>

        {/* wordmark that rises into view */}
        <div className="overflow-hidden">
          <motion.div initial={{ y: '60%' }} whileInView={{ y: 0 }} viewport={{ once: true }} transition={{ duration: 0.9, ease: [0.2, 0.9, 0.3, 1] }}
                      className="wordmark -mb-[0.1em] select-none text-center" aria-hidden="true">
            DEEPSENTINEL
          </motion.div>
        </div>
      </div>
    </footer>
  )
}
