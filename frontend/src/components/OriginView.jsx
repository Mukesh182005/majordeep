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

  return (
    <div className="space-y-6">
      {/* ── Banner ── */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border p-5"
        style={{ borderColor: 'rgba(0,229,255,0.2)', background: 'rgba(0,229,255,0.04)' }}>
        <div className="flex items-start gap-4">
          <div className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl"
            style={{ background: 'rgba(0,229,255,0.12)', color: '#00E5FF' }}>
            <Globe size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[0.625rem] font-black uppercase tracking-widest" style={{ color: '#71717a' }}>Media Origin Intelligence</p>
            <p className="mt-0.5 font-extrabold text-ink-primary" style={{ fontSize: 'clamp(1rem, 1.5vw, 1.25rem)', letterSpacing: '-0.03em' }}>
              {gen.likely_origin || 'Unknown'}
            </p>
            <p className="mt-1 text-[0.8125rem] text-ink-muted">
              Generator Family: <span className="font-semibold text-ink-primary">{gen.generator_family || '—'}</span>
            </p>
          </div>
          <ConfidencePill level={gen.confidence >= 0.75 ? 'HIGH' : gen.confidence >= 0.5 ? 'MEDIUM' : 'LOW'} />
        </div>
        {gen.evidence?.length > 0 && (
          <ul className="mt-4 space-y-1">
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
            { label: 'Manifest Present', value: prov.c2pa_present ? 'YES' : 'NOT DETECTED', ok: prov.c2pa_present },
            { label: 'Manifest Status', value: prov.manifest_status || '—', ok: prov.manifest_status === 'Valid' || prov.manifest_status === 'Not Detected' },
            { label: 'AI Assertion', value: prov.ai_assertion ? 'PRESENT' : 'ABSENT', ok: !prov.ai_assertion },
          ].map((row, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b last:border-0" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="text-[0.75rem] text-ink-muted">{row.label}</span>
              <span className="text-[0.75rem] font-bold mono"
                style={{ color: row.ok === true ? '#00E5FF' : row.ok === false ? '#FF3D00' : 'var(--text-primary)' }}>
                {row.value}
              </span>
            </div>
          ))}
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
                <span className="text-right text-[0.75rem] font-semibold" style={{ color: ok ? '#00E5FF' : '#FF3D00' }}>{val}</span>
              </div>
            )
          })}
        </motion.div>
      </div>

      {/* ── Source Discovery Status ── */}
      {srcDiscovery.status && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="rounded-2xl border p-4" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-1)' }}>
          <p className="text-[0.625rem] font-black uppercase tracking-widest mb-2" style={{ color: '#71717a' }}>Source Discovery</p>
          <p className="text-[0.8125rem] text-ink-muted">
            {srcDiscovery.note || 'No source discovery data available.'}
          </p>
        </motion.div>
      )}
    </div>
  )
}
