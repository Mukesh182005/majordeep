import { motion } from 'framer-motion'
import { Shield, Globe, CheckCircle } from './ui/Icons'

const ConfidencePill = ({ level }) => {
  const map = {
    HIGH:   { color: '#00E5FF', bg: 'rgba(0,229,255,0.1)' },
    MEDIUM: { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
    LOW:    { color: '#22c55e', bg: 'rgba(34,197,94,0.1)' },
  }
  const s = map[level] || map.MEDIUM
  return (
    <span className="text-[0.625rem] font-black uppercase tracking-widest px-2 py-0.5 rounded-full"
      style={{ color: s.color, background: s.bg, border: `1px solid ${s.color}40` }}>
      {level}
    </span>
  )
}

export default function OriginView({ mopci }) {
  if (!mopci) return (
    <div className="flex items-center justify-center h-40 text-ink-muted text-sm">
      No origin data available.
    </div>
  )

  const gen = mopci.generation_attribution || {}
  const prov = mopci.provenance || {}
  const phys = mopci.physical_world_consistency || {}
  const srcDiscovery = mopci.source_discovery || {}

  // Phase 31.6: Provenance status is decoupled from raw detector predictions
  let provenanceStatus = 'ORIGIN INCONCLUSIVE'
  let provenanceTone = 'neutral'
  if (prov.c2pa_present && prov.manifest_status === 'Valid') {
    provenanceStatus = 'VERIFIED PROVENANCE'
    provenanceTone = 'good'
  } else if (srcDiscovery.candidates && srcDiscovery.candidates.length > 0) {
    provenanceStatus = 'SOURCE CANDIDATE'
    provenanceTone = 'warn'
  } else if (srcDiscovery.status === 'NOT_FOUND') {
    provenanceStatus = 'NO SOURCE FOUND'
    provenanceTone = 'neutral'
  } else if (!mopci.provenance && !mopci.generation_attribution) {
    provenanceStatus = 'PROVENANCE UNAVAILABLE'
    provenanceTone = 'neutral'
  }

  return (
    <div className="space-y-6">
      {/* ── Banner: Provenance Status ── */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border p-5"
        style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-1)' }}>
        <div className="flex items-start gap-4">
          <div className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl"
            style={{ background: 'rgba(0,229,255,0.12)', color: '#00E5FF' }}>
            <Globe size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[0.625rem] font-black uppercase tracking-widest text-ink-muted">Media Provenance Status</p>
            <p className="mt-0.5 font-black text-ink-primary tracking-tight" style={{ fontSize: 'clamp(1.1rem, 1.6vw, 1.35rem)' }}>
              {provenanceStatus}
            </p>
            <p className="mt-1 text-[0.8125rem] text-ink-muted">
              Inferred Generator Pattern: <span className="font-semibold text-ink-primary">{gen.generator_family || 'Not established'}</span>
            </p>
            <p className="mt-2 text-xs text-ink-muted leading-relaxed">
              Analytical indicator based on detector response. Provenance and origin discovery are separate forensic questions from generative pattern detection.
            </p>
          </div>
          <ConfidencePill level={gen.confidence >= 0.75 ? 'HIGH' : gen.confidence >= 0.5 ? 'MEDIUM' : 'LOW'} />
        </div>
        {gen.evidence?.length > 0 && (
          <ul className="mt-4 pt-3 border-t border-subtle space-y-1">
            {gen.evidence.map((e, i) => (
              <li key={i} className="flex items-center gap-2 text-[0.75rem] text-ink-muted">
                <span style={{ color: '#00E5FF', fontSize: '0.5rem' }}>◆</span> {e}
              </li>
            ))}
          </ul>
        )}
      </motion.div>

      {/* ── 2-col: Provenance + Physical ── */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Provenance (C2PA) */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-2xl border p-5" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-1)' }}>
          <p className="text-[0.625rem] font-black uppercase tracking-widest mb-3" style={{ color: '#71717a' }}>C2PA / Content Credentials</p>
          {[
            { label: 'Manifest Present', value: prov.c2pa_present ? 'YES' : 'ABSENT', ok: prov.c2pa_present },
            { label: 'Manifest Status', value: prov.manifest_status || 'Not Detected', ok: prov.manifest_status === 'Valid' || prov.manifest_status === 'Not Detected' },
            { label: 'AI Assertion', value: prov.ai_assertion ? 'PRESENT' : 'ABSENT', ok: !prov.ai_assertion },
          ].map((row, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b last:border-0" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="text-[0.75rem] text-ink-muted">{row.label}</span>
              <span className="text-[0.75rem] font-bold mono"
                style={{ color: row.ok === true ? '#00E5FF' : 'var(--text-secondary)' }}>
                {row.value}
              </span>
            </div>
          ))}
          <p className="mt-3 text-[0.6875rem] text-ink-muted border-t border-subtle pt-2">
            Absence of Content Credentials (C2PA) does not establish that the media was AI-generated.
          </p>
        </motion.div>

        {/* Physical World Consistency */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="rounded-2xl border p-5" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-1)' }}>
          <p className="text-[0.625rem] font-black uppercase tracking-widest mb-3" style={{ color: '#71717a' }}>Physical World Consistency</p>
          {Object.entries(phys).map(([key, val], i) => {
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
            const ok = typeof val === 'string' && val.toLowerCase().includes('consistent') && !val.toLowerCase().includes('inconsistent')
            return (
              <div key={i} className="flex items-start justify-between gap-2 py-1.5 border-b last:border-0" style={{ borderColor: 'var(--border-subtle)' }}>
                <span className="text-[0.75rem] text-ink-muted">{label}</span>
                <span className="text-right text-[0.75rem] font-semibold" style={{ color: ok ? 'var(--status-good)' : 'var(--status-warn)' }}>{val}</span>
              </div>
            )
          })}
        </motion.div>
      </div>

      {/* ── Source Discovery Status ── */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
        className="rounded-2xl border p-4 space-y-2" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-1)' }}>
        <div className="flex items-center justify-between">
          <p className="text-[0.625rem] font-black uppercase tracking-widest text-ink-muted">Source Discovery & Intelligence</p>
          <span className="text-[0.6875rem] font-mono px-2 py-0.5 rounded bg-surface-2 text-ink-secondary">
            {srcDiscovery.candidates?.length ? `${srcDiscovery.candidates.length} SOURCE CANDIDATE(S)` : '0 CANDIDATES'}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs py-1">
          <div className="p-2 rounded border border-subtle bg-surface-2">
            <span className="text-ink-muted text-[0.65rem] block">Earliest Occurrence</span>
            <span className="font-mono font-bold text-ink-primary">NOT FOUND</span>
          </div>
          <div className="p-2 rounded border border-subtle bg-surface-2">
            <span className="text-ink-muted text-[0.65rem] block">Potential Sources</span>
            <span className="font-mono font-bold text-ink-primary">{srcDiscovery.candidates?.length || 0}</span>
          </div>
          <div className="p-2 rounded border border-subtle bg-surface-2">
            <span className="text-ink-muted text-[0.65rem] block">Provenance State</span>
            <span className="font-mono font-bold text-ink-primary">{provenanceStatus}</span>
          </div>
        </div>
        <p className="text-[0.8125rem] text-ink-muted pt-1">
          {srcDiscovery.note || 'No external source candidates were queried. Unverified web matches are classified as Source Candidates, never original sources unless cryptographically confirmed.'}
        </p>
      </motion.div>
    </div>
  )
}
