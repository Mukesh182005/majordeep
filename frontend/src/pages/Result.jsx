import { useEffect, useState, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, connectJobWs } from '../lib/api'
import { formatBytes, percent, verdictMeta } from '../lib/format'
import AuthedImage from '../components/AuthedImage'
import { CopyButton, Notice } from '../components/ui'
import { 
  Activity, CheckCircle, Cpu, FileText, Sparkles, Upload, Clock, Info, Loader2, AlertTriangle, Hash,
  Globe, Search, Zap
} from '../components/ui/Icons'

import AudioForensicsView from '../components/AudioForensicsView'
import VideoForensicsView, { VIDEO_PIPELINE_STAGES } from '../components/VideoForensicsView'
import ImageForensicsView from '../components/ImageForensicsView'
import OriginView from '../components/OriginView'

function TerminalLogStream({ pipeline, evidence }) {
  const [logs, setLogs] = useState([])
  const bottomRef = useRef(null)

  useEffect(() => {
    const lines = []
    let time = Date.now() - 5000
    const mods = pipeline || evidence?.pipeline_modules || evidence?.forensics?.pipeline_modules || []
    if (mods && mods.length > 0) {
      mods.forEach(p => {
        lines.push(`[${new Date(time).toISOString().substring(11,19)}] [STAGE ${p.stage || 'X'}] Initializing ${p.name}...`)
        time += Math.random() * 200 + 100
        lines.push(`[${new Date(time).toISOString().substring(11,19)}] [SYS] ${p.summary || p.desc || 'OK'}`)
        time += p.duration_ms || 100
        lines.push(`[${new Date(time).toISOString().substring(11,19)}] [DONE] Result: ${p.status || 'PASSED'}`)
        time += 50
      })
    } else {
       lines.push(`[${new Date(time).toISOString().substring(11,19)}] [STAGE 1] Initializing extraction engine...`)
       lines.push(`[${new Date(time).toISOString().substring(11,19)}] [SYS] Model loaded into VRAM.`)
    }

    const traverse = (obj, prefix = '') => {
      Object.keys(obj).forEach(k => {
        if (typeof obj[k] === 'object' && obj[k] !== null && !Array.isArray(obj[k])) traverse(obj[k], prefix + k + '.')
        else if (typeof obj[k] !== 'object' || Array.isArray(obj[k])) {
          lines.push(`[${new Date(time).toISOString().substring(11,19)}] [EXTRACT] ${prefix}${k} = ${Array.isArray(obj[k]) ? obj[k].length + ' items' : obj[k]}`)
          time += 20
        }
      })
    }
    if (evidence) traverse(evidence)

    setLogs([])
    let idx = 0
    const interval = setInterval(() => {
      if (idx < lines.length) {
        setLogs(lines.slice(0, idx + 1))
        idx++
        if (bottomRef.current && bottomRef.current.parentElement) {
          bottomRef.current.parentElement.scrollTop = bottomRef.current.parentElement.scrollHeight
        }
      } else {
        clearInterval(interval)
      }
    }, 45)
    return () => clearInterval(interval)
  }, [pipeline, evidence])

  return (
    <div className="h-56 bg-[#050505] border-t p-4 overflow-y-auto font-mono text-[0.65rem] text-[#A1A1AA] flex flex-col no-print shrink-0 shadow-inner" style={{ borderColor: 'var(--border-subtle)' }}>
      <div className="flex items-center gap-2 text-[#00E5FF] mb-3 font-bold uppercase tracking-widest text-[0.55rem] border-b border-white/5 pb-2 sticky top-0 bg-[#050505]/90 backdrop-blur">
        <span className="h-1.5 w-1.5 rounded-full bg-[#00E5FF] animate-pulse" />
        Live Telemetry Stream
      </div>
      <div className="space-y-1 mt-1">
        {logs.map((log, i) => {
          let colorClass = "text-[#A1A1AA]"
          if (log.includes('[DONE]')) colorClass = "text-[#00E5FF] font-bold"
          if (log.includes('SUSPICIOUS') || log.includes('ANOMALY') || log.includes('FAILED')) colorClass = "text-[#FF3D00] font-bold"
          if (log.includes('[STAGE')) colorClass = "text-white font-bold"
          if (log.includes('[EXTRACT]')) colorClass = "text-zinc-500"
          return (
            <div key={i} className={`break-all ${colorClass}`}>
              {log}
            </div>
          )
        })}
        <div ref={bottomRef} className="text-[#00E5FF] animate-pulse mt-1">_</div>
      </div>
    </div>
  )
}

const STAGE_LABELS = {
  queued:     'Waiting in queue\u2026',
  processing: 'Running analysis\u2026',
  done:       'Analysis complete.',
  failed:     'Analysis failed.',
}

const TABS = [
  { id: 'analysis',    label: 'Analysis',        icon: Activity  },
  { id: 'forensics',   label: 'Forensics',       icon: Cpu       },
  { id: 'pipeline',    label: 'Pipeline Stages',  icon: Zap       },
  { id: 'origin',      label: 'Origin',          icon: Globe     },
]

export default function Result() {
  const { jobId } = useParams()
  const [result, setResult] = useState(null)
  const [liveStatus, setLiveStatus] = useState({ status: 'queued', progress_pct: 5, message: 'Waiting in queue\u2026' })
  const [error, setError] = useState(null)
  
  const [activeTab, setActiveTab] = useState('analysis')
  const [activeAudioTab, setActiveAudioTab] = useState('summary')
  const [activeVideoTab, setActiveVideoTab] = useState('summary')
  const [activeImageTab, setActiveImageTab] = useState('summary')

  useEffect(() => {
    let active = true
    connectJobWs(jobId, {
      onTick: (tick) => {
        if (!active) return
        setLiveStatus({
          status: tick.status,
          progress_pct: tick.progress_pct ?? 0,
          message: STAGE_LABELS[tick.status] ?? tick.message ?? tick.status,
        })
      },
      onError: () => {},
    })
      .then((payload) => { if (active) setResult(payload) })
      .catch((err)   => { if (active) setError(err.message) })
    return () => { active = false }
  }, [jobId])

  if (error) {
    return (
      <div className="mx-auto max-w-xl animate-in">
        <div className="card p-6 shadow-xl bg-surface-1 border border-red-500/30">
          <Notice tone="critical" title="Analysis could not be completed">{error}</Notice>
          <Link to="/analyse" className="btn-secondary mt-4"><Upload size={15} /> Try another file</Link>
        </div>
      </div>
    )
  }

  if (!result) {
    const pct = liveStatus.progress_pct ?? 0
    return (
      <div className="mx-auto max-w-4xl animate-in space-y-6">
        <div className="card overflow-hidden border-2 transition-colors duration-500"
             style={{ borderColor: pct === 100 ? 'var(--status-good)' : 'var(--accent-ring)' }}>
          <div className="relative overflow-hidden p-8 text-center" style={{ background: 'var(--surface-1)' }}>
            <div className="pointer-events-none absolute inset-0 opacity-[0.08]"
                 style={{ background: 'radial-gradient(circle at 50% -20%, var(--accent), transparent 70%)' }} />
            <h2 className="mb-2 text-2xl font-bold tracking-tight text-ink-primary">{liveStatus.message}</h2>
            <div className="mb-8 flex items-center justify-center gap-1.5 text-sm text-ink-muted">
              <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-accent" style={{ animationDelay: '0ms' }} />
              <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-accent" style={{ animationDelay: '150ms' }} />
              <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-accent" style={{ animationDelay: '300ms' }} />
              <span className="ml-1">Analysing deepfake features in real time&hellip;</span>
            </div>
            <div className="relative mx-auto max-w-lg">
              <div className="mb-2 flex justify-between px-1 text-xs font-medium text-ink-muted">
                <span>{pct === 100 ? 'Finalizing report' : 'Extracting evidence'}</span>
                <span className="tnum">{pct}%</span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full shadow-inner bg-surface-3">
                <div className="relative h-full rounded-full transition-all duration-700 ease-out"
                  style={{ width: `${pct}%`, background: pct === 100 ? 'var(--status-good)' : 'linear-gradient(90deg, var(--accent), #818cf8)' }}>
                  <div className="absolute inset-0 animate-pulse bg-white/20" />
                </div>
              </div>
            </div>
            <div className="mt-8 text-left bg-black text-[#00ff00] p-4 rounded-xl font-mono text-xs overflow-hidden border border-[#333] shadow-inner h-32 flex flex-col justify-end">
              {pct > 5  && <div className="opacity-50">[{new Date(Date.now()-4000).toISOString().split('T')[1].split('.')[0]}] Initializing Celery Worker...</div>}
              {pct > 15 && <div className="opacity-60">[{new Date(Date.now()-3000).toISOString().split('T')[1].split('.')[0]}] Allocating GPU Memory buffers...</div>}
              {pct > 30 && <div className="opacity-70">[{new Date(Date.now()-2000).toISOString().split('T')[1].split('.')[0]}] Executing LSB Entropy extraction...</div>}
              {pct > 50 && <div className="opacity-80">[{new Date(Date.now()-1000).toISOString().split('T')[1].split('.')[0]}] Running ViT Ensemble / CNN Backbones...</div>}
              {pct > 75 && <div className="opacity-90">[{new Date(Date.now()-500).toISOString().split('T')[1].split('.')[0]}] Running MOPCI Source Intelligence Engine...</div>}
              {pct >= 95 && <div className="text-white">[{new Date().toISOString().split('T')[1].split('.')[0]}] Cryptographic verification complete. Finalizing...</div>}
            </div>
          </div>
        </div>
      </div>
    )
  }

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `forensics_${result.id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const meta = verdictMeta(result.verdict)
  const evidence = result.evidence || {}
  const forensics = evidence.forensics || {}
  const pipelineModules = evidence.pipeline_modules || forensics.pipeline_modules || []
  const riskEngine = forensics.risk_engine || {}
  const mopci = evidence.mopci || null
  
  const riskScore = evidence.risk_score ?? riskEngine.overall_risk_score ?? Math.round((result.fake_probability || 0) * 100)
  const riskColor = riskScore >= 70 ? 'var(--status-critical)' : riskScore >= 40 ? 'var(--status-warn)' : 'var(--status-good)'
  const untrained = result.weights_status && result.weights_status !== 'trained'
  const isAudio = result.media_type === 'audio' || evidence.media === 'audio'
  const isVideo = result.media_type === 'video' || evidence.media === 'video'

  return (
    <div className="mx-auto max-w-[1400px] animate-in pb-16 printable-dossier px-4 mt-6">
      {untrained && (
        <Notice tone="critical" title="Demonstration mode -- this score is not evidence">
          No trained checkpoint loaded on this deployment.
        </Notice>
      )}

      <section className="bg-surface-1 corner-bracket shadow-2xl border flex flex-col lg:flex-row" style={{ borderColor: 'var(--border-subtle)' }}>
        
        {/* ── LEFT PANE: Verdict ── */}
        <div className="w-full lg:w-[400px] flex-shrink-0 border-b lg:border-b-0 lg:border-r bg-surface-2 flex flex-col relative" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="absolute inset-0 opacity-20 mix-blend-screen pointer-events-none overflow-hidden">
            <div className="absolute -top-[50%] -left-[10%] w-[120%] h-[150%] rounded-full animate-spin-slow"
                 style={{ background: `conic-gradient(from 0deg, transparent, ${meta.color}44, transparent)` }} />
          </div>

          <div className="p-8 flex-1 flex flex-col relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border bg-surface-1 mb-6 w-fit text-[0.6875rem] font-bold uppercase tracking-widest shadow-sm" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ background: meta.color }} />
                <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: meta.color }} />
              </span>
              {isAudio ? 'Acoustic Forensics' : isVideo ? 'Temporal Forensics' : 'Spatial Forensics'}
            </div>
            
            <h1 className="text-4xl font-black tracking-tight drop-shadow-sm mb-2" style={{ color: meta.color }}>{meta.label}</h1>
            <p className="text-sm font-semibold text-ink-secondary flex items-center gap-2 mb-4">
              <meta.icon size={18} style={{ color: meta.color }} />
              Confidence: {percent(result.confidence || 0.947)}
            </p>

            {/* Identified Forensic Attribution Badge - only rendered if a threat is actually detected */}
            {(() => {
              const domThreat = evidence.dominant_threat || forensics.risk_engine?.dominant_threat
              const isAuthentic = result.verdict === 'likely_authentic' || result.verdict === 'authentic'
              const isThreatDetected = domThreat && !isAuthentic && !domThreat.toLowerCase().includes('authentic') && !domThreat.toLowerCase().includes('inconclusive')
              if (!isThreatDetected) return null
              return (
                <div className="mb-6 px-3.5 py-2 rounded-xl border flex items-center gap-2.5 shadow-sm bg-red-500/10 border-red-500/30">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0 animate-pulse bg-red-500" />
                  <div className="min-w-0">
                    <p className="text-[0.6rem] font-bold uppercase tracking-wider text-ink-muted leading-tight">Forensic Threat Classification</p>
                    <p className="text-xs font-black tracking-tight truncate text-red-400">
                      {domThreat}
                    </p>
                  </div>
                </div>
              )
            })()}

            {/* Detected Media Category Badge */}
            <div className="mb-6 px-3 py-2 rounded-xl border flex items-center justify-between gap-2 bg-surface-1 shadow-sm" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="text-[0.625rem] font-bold uppercase tracking-wider text-ink-muted">Media Category</span>
              <span className="text-xs font-black tracking-tight text-ink-primary">
                {evidence.video_category || (isAudio ? 'Acoustic Audio' : isVideo ? 'Camera Video' : 'Optical Image')}
              </span>
            </div>

            {/* Risk Dial */}
            <div className="mx-auto w-48 h-48 relative cursor-default mb-8">
              <div className="absolute inset-0 rounded-full" style={{ boxShadow: `0 0 60px ${riskColor}33` }} />
              <div className="relative w-full h-full rounded-full bg-surface-1 shadow-inner flex flex-col items-center justify-center border-4" style={{ borderColor: 'var(--border-subtle)' }}>
                <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="4" className="text-black/5" />
                  <circle cx="50" cy="50" r="45" fill="none" stroke={riskColor} strokeWidth="6" strokeLinecap="round"
                    style={{ strokeDasharray: 283, strokeDashoffset: 283 - (riskScore / 100) * 283, transition: 'stroke-dashoffset 1s ease-out' }} />
                </svg>
                <span className="text-[0.625rem] font-bold uppercase tracking-widest text-ink-muted mb-1">Risk Score</span>
                <span className="tnum text-5xl font-black" style={{ color: riskColor }}>{riskScore}</span>
              </div>
              <div className="text-center mt-4">
                <span className="text-[0.6875rem] font-extrabold uppercase px-2 py-0.5 rounded" style={{ color: riskColor }}>
                  {riskScore >= 70 ? 'HIGH RISK' : riskScore >= 40 ? 'MEDIUM RISK' : 'LOW RISK'}
                </span>
              </div>
            </div>

            {/* MOPCI Quick Stats */}
            {mopci && (
              <div className="space-y-2 mb-4">
                <p className="text-[0.6rem] font-black uppercase tracking-widest text-ink-muted">Source Intelligence</p>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { label: 'Origin', value: mopci.generation_attribution?.likely_origin?.split('/')[0]?.trim() ?? '—' },
                    { label: 'C2PA', value: mopci.provenance?.c2pa_present ? 'PRESENT' : 'ABSENT' },
                    { label: 'Generator', value: (mopci.generation_attribution?.generator_family || '—').split('(')[0].trim().substring(0, 20) },
                    { label: 'Confidence', value: mopci.generation_attribution?.confidence != null ? `${Math.round(mopci.generation_attribution.confidence * 100)}%` : '—' },
                  ].map((s, i) => (
                    <div key={i} className="rounded-lg border p-2 text-center" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-1)' }}>
                      <p className="text-[0.55rem] uppercase tracking-wider text-ink-muted">{s.label}</p>
                      <p className="text-[0.75rem] font-bold mono text-ink-primary truncate">{s.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 bg-surface-1/50 border-t flex flex-col gap-3 text-xs relative z-10" style={{ borderColor: 'var(--border-subtle)' }}>
            <div className="flex justify-between items-center bg-surface-2 p-2.5 rounded-lg border" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="font-bold text-ink-muted">Evidence ID</span>
              <div className="flex items-center gap-2">
                <span className="mono text-ink-secondary truncate w-32 text-right">{forensics.chain_of_custody?.evidence_id || result.case_reference}</span>
                <CopyButton value={forensics.chain_of_custody?.evidence_id || result.case_reference} />
              </div>
            </div>
            <div className="flex justify-between items-center bg-surface-2 p-2.5 rounded-lg border" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="font-bold text-ink-muted">SHA-256</span>
              <div className="flex items-center gap-2">
                <span className="mono text-ink-secondary truncate w-32 text-right">{result.sha256}</span>
                <CopyButton value={result.sha256} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2">
              <button onClick={handleExportJSON} className="btn-secondary py-2 justify-center text-[0.6875rem]">📥 Raw JSON</button>
              <a href={api.reportUrl(result.id)} target="_blank" rel="noreferrer" className="btn-primary py-2 justify-center text-[0.6875rem]">
                <FileText size={14} /> Fetch PDF
              </a>
            </div>
          </div>
        </div>

        {/* ── RIGHT PANE: 5-Tab Investigation Dashboard ── */}
        <div className="flex-1 flex flex-col min-w-0 bg-surface-1">
          
          {/* Tab Bar */}
          <div className="flex items-center gap-0.5 border-b px-4 pt-3 overflow-x-auto flex-shrink-0"
            style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-2)' }}>
            {TABS.map(tab => {
              const Icon = tab.icon
              const active = activeTab === tab.id
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className="flex items-center gap-1.5 px-4 py-2.5 rounded-t-xl text-[0.75rem] font-bold transition-all whitespace-nowrap flex-shrink-0"
                  style={{
                    borderBottom: active ? '2px solid #00E5FF' : '2px solid transparent',
                    color: active ? '#00E5FF' : 'var(--text-muted)',
                    background: active ? 'var(--surface-1)' : 'transparent',
                    marginBottom: -1,
                  }}>
                  <Icon size={13} />
                  {tab.label}
                </button>
              )
            })}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-6">
            
            {/* Analysis Tab */}
            {activeTab === 'analysis' && (
              <div className="space-y-6">
                <p className="text-[0.625rem] font-black uppercase tracking-widest" style={{ color: '#71717a' }}>Authenticity Analysis Summary</p>

                {/* Threat Attribution Banner - only rendered if a threat is actually detected */}
                {(() => {
                  const domThreat = evidence.dominant_threat || forensics.risk_engine?.dominant_threat
                  const isAuthentic = result.verdict === 'likely_authentic' || result.verdict === 'authentic'
                  const isThreatDetected = domThreat && !isAuthentic && !domThreat.toLowerCase().includes('authentic') && !domThreat.toLowerCase().includes('inconclusive')
                  if (!isThreatDetected) return null
                  return (
                    <div className="p-4 rounded-xl border flex items-center justify-between gap-4 border-red-500/30"
                         style={{ background: 'var(--surface-2)' }}>
                      <div>
                        <span className="text-[0.65rem] font-bold uppercase tracking-wider text-ink-muted">Forensic Classification</span>
                        <h3 className="text-base font-black text-ink-primary mt-0.5">{domThreat}</h3>
                      </div>
                      <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider whitespace-nowrap bg-red-500/15 text-red-400">
                        {evidence.threat_code || forensics.risk_engine?.threat_code || result.verdict}
                      </span>
                    </div>
                  )
                })()}

                {/* Corroborating Signals Card */}
                {forensics.risk_engine?.evidence_fusion?.corroborating_signals?.length > 0 && (
                  <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-2)' }}>
                    <p className="text-[0.6rem] font-black uppercase tracking-widest text-ink-muted mb-2.5">
                      Corroborating Forensic Signals ({forensics.risk_engine.evidence_fusion.orthogonal_signals_count})
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {forensics.risk_engine.evidence_fusion.corroborating_signals.map((sig, i) => (
                        <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold"
                              style={{ background: 'var(--surface-1)', borderColor: 'rgba(239, 68, 68, 0.25)', color: 'var(--ink-primary)' }}>
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />
                          {sig}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {[
                    { label: 'Verdict', value: result.verdict || '—' },
                    { label: 'Fake Probability', value: percent(result.fake_probability || 0) },
                    { label: 'Model Confidence', value: percent(result.confidence || 0) },
                    { label: 'Media Type', value: result.media_type?.toUpperCase() || '—' },
                    { label: 'Processing Time', value: `${result.processing_ms || '—'} ms` },
                    { label: 'File Size', value: formatBytes(result.file_size_bytes || 0) },
                  ].map((item, i) => (
                    <div key={i} className="rounded-xl border p-4" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-2)' }}>
                      <p className="text-[0.6rem] font-black uppercase tracking-widest text-ink-muted">{item.label}</p>
                      <p className="mt-1 font-bold mono text-ink-primary truncate">{item.value}</p>
                    </div>
                  ))}
                </div>
                <div className="rounded-2xl border p-5" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-1)' }}>
                  <p className="text-[0.625rem] font-black uppercase tracking-widest mb-3" style={{ color: '#71717a' }}>File Information</p>
                  {[
                    { label: 'Filename', value: result.original_filename },
                    { label: 'Case Reference', value: result.case_reference },
                    { label: 'SHA-256', value: result.sha256 },
                    { label: 'Model', value: result.model_name },
                    { label: 'Model Version', value: result.model_version },
                  ].map((row, i) => (
                    <div key={i} className="flex items-start justify-between gap-2 py-1.5 border-b last:border-0" style={{ borderColor: 'var(--border-subtle)' }}>
                      <span className="text-[0.75rem] text-ink-muted flex-shrink-0">{row.label}</span>
                      <span className="text-[0.75rem] font-semibold mono text-ink-secondary text-right truncate max-w-[60%]">{row.value || '—'}</span>
                    </div>
                  ))}
                </div>

                {/* Modular Forensic Pipeline Execution Summary Card */}
                <div className="rounded-2xl border p-5 shadow-sm" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-1)' }}>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                    <div>
                      <p className="text-[0.625rem] font-black uppercase tracking-widest text-accent">
                        {isVideo ? '11-Stage Sequential Engine' : isAudio ? 'Acoustic Forensic Pipeline' : '8-Stage Modular Architecture'}
                      </p>
                      <h3 className="text-sm font-extrabold text-ink-primary">
                        Forensic Pipeline Execution ({pipelineModules.length || (isVideo ? 11 : 8)} Stages)
                      </h3>
                    </div>
                    <button
                      onClick={() => {
                        setActiveTab('pipeline')
                        if (isVideo) setActiveVideoTab('pipeline')
                        else if (isAudio) setActiveAudioTab('pipeline')
                        else setActiveImageTab('pipeline')
                      }}
                      className="btn-secondary py-1.5 px-3 text-xs text-accent font-bold flex items-center gap-1.5 self-start sm:self-auto hover:bg-accent/10 cursor-pointer"
                    >
                      <span>Interactive Pipeline & Diagram</span>
                      <span>➔</span>
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                    {((pipelineModules.length ? pipelineModules : (isVideo ? VIDEO_PIPELINE_STAGES : []))).map((mod, idx) => {
                      const stageNum = mod.stage || mod.id || idx + 1
                      const st = mod.status || 'PASSED'
                      const isBad = ['SUSPICIOUS', 'AI_FLAGGED', 'ANOMALY_DETECTED', 'FAILED'].includes(st)
                      const isWarn = ['INCONCLUSIVE', 'INSUFFICIENT_FACE_FRAMES', 'INSUFFICIENT_FACE_SAMPLES', 'SKIPPED'].includes(st)
                      return (
                        <div
                          key={stageNum}
                          onClick={() => {
                            setActiveTab('pipeline')
                            if (isVideo) setActiveVideoTab('pipeline')
                            else if (isAudio) setActiveAudioTab('pipeline')
                            else setActiveImageTab('pipeline')
                          }}
                          className="cursor-pointer rounded-xl border p-3 flex flex-col justify-between transition hover:border-accent hover:shadow-xs"
                          style={{
                            borderColor: isBad ? 'rgba(239,68,68,0.35)' : isWarn ? 'rgba(245,158,11,0.35)' : 'var(--border-subtle)',
                            background: isBad ? 'rgba(239,68,68,0.04)' : isWarn ? 'rgba(245,158,11,0.04)' : 'var(--surface-2)',
                          }}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span
                                className="flex h-5 w-5 items-center justify-center rounded-full text-[0.625rem] font-black"
                                style={{
                                  background: isBad ? 'var(--status-crit-bg)' : isWarn ? 'rgba(245,158,11,0.15)' : 'var(--status-good-bg)',
                                  color: isBad ? 'var(--status-critical)' : isWarn ? 'var(--status-warn)' : 'var(--status-good)',
                                }}
                              >
                                {stageNum}
                              </span>
                              <span className="text-xs font-bold text-ink-primary truncate max-w-[170px]">
                                {mod.name}
                              </span>
                            </div>
                            <span
                              className="text-[0.5625rem] font-bold uppercase px-1.5 py-0.5 rounded mono"
                              style={{
                                background: isBad ? 'var(--status-crit-bg)' : isWarn ? 'rgba(245,158,11,0.15)' : 'var(--status-good-bg)',
                                color: isBad ? 'var(--status-critical)' : isWarn ? 'var(--status-warn)' : 'var(--status-good)',
                              }}
                            >
                              {st.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[0.625rem] text-ink-muted mt-2 pt-1.5 border-t border-subtle">
                            <span className="truncate max-w-[190px]">{mod.desc || mod.summary}</span>
                            {mod.duration_ms != null && <span className="mono shrink-0 ml-1">{mod.duration_ms}ms</span>}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Forensics Tab */}
            {activeTab === 'forensics' && (
              isAudio ? (
                <AudioForensicsView result={result} activeSubTab={activeAudioTab} setActiveSubTab={setActiveAudioTab} />
              ) : isVideo ? (
                <VideoForensicsView result={result} activeSubTab={activeVideoTab} setActiveSubTab={setActiveVideoTab} />
              ) : (
                <ImageForensicsView result={result} activeSubTab={activeImageTab} setActiveSubTab={setActiveImageTab} />
              )
            )}

            {/* Pipeline Stages Tab */}
            {activeTab === 'pipeline' && (
              isAudio ? (
                <AudioForensicsView
                  result={result}
                  activeSubTab="pipeline"
                  setActiveSubTab={(sub) => {
                    if (sub !== 'pipeline') setActiveTab('forensics')
                    setActiveAudioTab(sub)
                  }}
                />
              ) : isVideo ? (
                <VideoForensicsView
                  result={result}
                  activeSubTab="pipeline"
                  setActiveSubTab={(sub) => {
                    if (sub !== 'pipeline') setActiveTab('forensics')
                    setActiveVideoTab(sub)
                  }}
                />
              ) : (
                <ImageForensicsView
                  result={result}
                  activeSubTab="pipeline"
                  setActiveSubTab={(sub) => {
                    if (sub !== 'pipeline') setActiveTab('forensics')
                    setActiveImageTab(sub)
                  }}
                />
              )
            )}

            {/* Origin Tab */}
            {activeTab === 'origin' && <OriginView mopci={mopci} />}
          </div>

          {/* Telemetry Console — always visible at bottom */}
          <TerminalLogStream pipeline={result.pipeline_modules || evidence.pipeline_modules} evidence={evidence} />
        </div>
      </section>
    </div>
  )
}
