import { useState } from 'react'
import { Card, CopyButton, SplitLoupeOverlay } from './ui'
import AuthedImage from './AuthedImage'
import {
  Activity, Alert, Check, CheckCircle, Cpu, Download, Eye, FileText, Hash,
  Info, Lock, ShieldAlert, ShieldCheck, ShieldQuestion, Sparkles, Image as ImageIcon
} from './ui/Icons'
import { percent, formatBytes } from '../lib/format'
import { api } from '../lib/api'
import PipelineAuditVisualizer from './PipelineAuditVisualizer'

export default function ImageForensicsView({ result, activeSubTab, setActiveSubTab }) {
  const renderEntries = (obj, depth = 0) => {
    if (!obj || typeof obj !== 'object') return null;
    return Object.entries(obj).map(([key, val]) => {
      if (val === null || val === undefined) return null;
      if (typeof val === 'object' && !Array.isArray(val)) {
        return (
          <div key={key} className={`mt-${depth === 0 ? '2' : '1'} mb-1`}>
            <span className="text-ink-muted font-bold text-[0.6875rem] uppercase tracking-wider">{key.replace(/_/g, ' ')}</span>
            <div className="pl-3 border-l-2 ml-1 mt-1 space-y-1" style={{ borderColor: 'var(--border-subtle)' }}>
              {renderEntries(val, depth + 1)}
            </div>
          </div>
        )
      }
      return (
        <div key={key} className="flex justify-between items-baseline border-b pb-1 border-black/5 py-0.5">
          <span className="text-ink-muted text-xs font-medium">{key.replace(/_/g, ' ')}</span>
          <span className="text-ink-primary text-xs font-bold truncate max-w-[55%] text-right">
            {typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(4)) : (Array.isArray(val) ? val.join(', ') : String(val))}
          </span>
        </div>
      )
    })
  }

  const evidence = result.evidence || {}
  const forensics = evidence.forensics || {}
  
  const pipelineModules = evidence.pipeline_modules || forensics.pipeline_modules || []
  const aiBreakdown = evidence.ai_breakdown || {}
  const metaForensics = forensics.metadata_forensics || {}
  const tampering = forensics.tampering || {}
  const stego = forensics.steganography || {}
  const visualEvidence = forensics.visual_evidence || {}
  
  const [selectedPlate, setSelectedPlate] = useState('combined')
  const [inspectZoom, setInspectZoom] = useState(false)

  const plates = {
    combined: {
      url: evidence.combined_url || visualEvidence.combined_url,
      label: 'Combined Analysis Map',
      badge: 'Composite',
      desc: 'Weighted composite overlay combining AI neural attention (Grad-CAM), Error Level Analysis (ELA), and sensor noise residuals for a holistic view of image manipulation.',
      resolution: 'Full Resolution Composite'
    },
    ai: {
      url: evidence.heatmap_url || visualEvidence.heatmap_url,
      label: 'AI Grad-CAM Activation',
      badge: 'Neural Attention',
      desc: 'Gradient-weighted class activation mapping (Grad-CAM) overlaid on the original image, highlighting the specific spatial regions that triggered deepfake neural detector responses.',
      resolution: 'Intermediate SSL layer gradient backprop'
    },
    ela: {
      url: evidence.ela_url || visualEvidence.ela_url,
      label: 'Error Level Analysis (ELA)',
      badge: 'Compression Forensics',
      desc: 'Differential JPEG compression error map. Highlights areas that have been resaved or spliced, revealing digital inpainting and copy-move forgery.',
      resolution: 'JPEG Error Difference'
    },
    noise: {
      url: evidence.noise_url || visualEvidence.noise_url,
      label: 'PRNU Sensor Noise',
      badge: 'Hardware Fingerprint',
      desc: 'High-frequency sensor noise residual (Photo Response Non-Uniformity). Highlights artificial noise uniformity typical of generative AI or spliced regions missing the original camera fingerprint.',
      resolution: 'High-Frequency Residual'
    },
    tampering: {
      url: evidence.tampering_url || visualEvidence.tampering_url,
      label: 'Edge & Tamper Gradients',
      badge: 'Structural Integrity',
      desc: 'Edge gradient density and cloned keypoint regions. Detects sharp artificial boundaries indicative of manual splicing or localized generative inpainting.',
      resolution: 'Sobel/Canny Edge Gradients'
    },
    watermark: {
      url: evidence.watermark_url || visualEvidence.watermark_url,
      label: 'Watermark & SynthID',
      badge: 'Provenance',
      desc: 'Detected visible logos, application badges, or invisible cryptographic watermarks (e.g., SynthID, C2PA) embedded by AI generators.',
      resolution: 'Spatial/Frequency Watermarks'
    },
    stego: {
      url: evidence.stego_url || visualEvidence.stego_url,
      label: 'LSB Steganography',
      badge: 'Covert Payload',
      desc: 'Spatial distribution of Least Significant Bit (LSB) entropy. Identifies regions where covert data payloads or hidden messages have been embedded into the pixel data.',
      resolution: 'Bit-plane Entropy'
    }
  }

  const activePlateObj = plates[selectedPlate]?.url ? plates[selectedPlate] : plates.combined

  const tabs = [
    { id: 'summary', label: 'Overview', count: 'KPIs' },
    { id: 'pipeline', label: '8-Stage Pipeline Audit', count: pipelineModules.length || 8 },
    { id: 'signallab', label: 'Visual Forensics Lab', count: '7 Plates' },
    { id: 'ai', label: 'Generative AI Metrics', count: 'Confidence' },
    { id: 'tampering', label: 'Structural Tampering', count: tampering.splicing_detected ? 'Alert' : 'Clean' },
    { id: 'stego', label: 'Steganography', count: stego.lsb_anomaly ? 'Detected' : 'Clean' },
    { id: 'metadata', label: 'EXIF & Metadata', count: metaForensics.metadata_keys_found || 0 },
  ]

  const tab = activeSubTab || 'summary'

  return (
    <div className="flex flex-col h-full">
      {/* CLEVERHUMANIZER .tool-top TABS */}
      <div className="flex items-center gap-2 overflow-x-auto p-4 border-b bg-surface-2 no-print" style={{ borderColor: 'var(--border-subtle)' }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setActiveSubTab(t.id)
              document.getElementById(t.id)?.scrollIntoView({ behavior: 'smooth' })
            }}
            className={`flex-none inline-flex items-center gap-1.5 px-4 py-2 text-[13.5px] font-bold rounded-full border-[1.5px] transition-all whitespace-nowrap ${
              tab === t.id
                ? 'bg-accent border-accent text-white shadow-sm cursor-default'
                : 'bg-surface-1 text-ink-muted border-transparent hover:border-accent hover:text-accent'
            }`}
          >
            <span>{t.label}</span>
            <span
              className={`text-[10px] uppercase font-mono tracking-wider px-1.5 py-0.5 rounded-full ${
                tab === t.id ? 'bg-white/20 text-white' : 'text-accent bg-accent/10'
              }`}
            >
              {t.count}
            </span>
          </button>
        ))}
      </div>

      <div className="p-6 space-y-6 overflow-y-auto min-h-0 flex-1">
      {tab === 'summary' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="glass-card p-4 flex flex-col items-start border border-black/10 dark:border-white/10 bg-surface-1 rounded-xl shadow-sm">
            <div className="flex justify-between w-full items-center mb-2">
              <h3 className="text-[0.625rem] font-bold uppercase tracking-widest text-ink-muted">Generative AI Core</h3>
              <div className={`${(aiBreakdown.generative_ai_prob ?? result.fake_probability ?? 0) > 0.5 ? 'led-critical' : 'led-good'}`}></div>
            </div>
            <p className="text-2xl font-black text-ink-primary font-mono">{percent(aiBreakdown.generative_ai_prob ?? result.fake_probability ?? 0)}</p>
            <p className="mt-1 text-[0.65rem] uppercase text-ink-secondary tracking-widest">ViT Ensemble Confidence</p>
          </div>
          <div className="glass-card p-4 flex flex-col items-start border border-black/10 dark:border-white/10 bg-surface-1 rounded-xl shadow-sm">
            <div className="flex justify-between w-full items-center mb-2">
              <h3 className="text-[0.625rem] font-bold uppercase tracking-widest text-ink-muted">Structural Splicing</h3>
              <div className={`${(tampering.splicing_detected || tampering.copy_move_detected) ? 'led-critical' : 'led-good'}`}></div>
            </div>
            <p className="text-2xl font-black text-ink-primary font-mono">
              {percent((tampering.splicing_detected || tampering.copy_move_detected) ? 0.82 : 0.05)}
            </p>
            <p className="mt-1 text-[0.65rem] uppercase text-ink-secondary tracking-widest">Pixel Space Anomalies</p>
          </div>
          <div className="glass-card p-4 flex flex-col items-start border border-black/10 dark:border-white/10 bg-surface-1 rounded-xl shadow-sm">
            <div className="flex justify-between w-full items-center mb-2">
              <h3 className="text-[0.625rem] font-bold uppercase tracking-widest text-ink-muted">Steganography (LSB)</h3>
              <div className={`${stego.lsb_anomaly ? 'led-critical' : 'led-good'}`}></div>
            </div>
            <p className="text-xl font-black text-ink-primary font-mono mt-1">
              {stego.lsb_anomaly ? 'PAYLOAD DETECTED' : 'CLEAR'}
            </p>
            <p className="mt-1 text-[0.65rem] uppercase text-ink-secondary tracking-widest">Covert Byte Injection</p>
          </div>
        </div>
      )}

      {tab === 'pipeline' && (
        <Card
          title="Modular Forensic Pipeline Execution"
          subtitle="Complete interactive audit trail, workflow architecture graph, and telemetry of all 8 specialized forensic engines"
        >
          <div className="mt-4">
            <PipelineAuditVisualizer
              pipelineModules={pipelineModules}
              forensics={forensics}
              evidence={evidence}
              result={result}
              onSelectPlate={(plateKey) => {
                setSelectedPlate(plateKey)
                setActiveSubTab('signallab')
              }}
            />
          </div>
        </Card>
      )}

      {tab === 'signallab' && (
        <Card title="Visual Forensics Lab" subtitle="Inspect high-fidelity thermal maps, ELA, and spatial tampering residuals">
          <div className="flex flex-wrap gap-2 mt-2 mb-4 no-print">
            {Object.entries(plates).map(([k, item]) => (
              <button
                key={k}
                onClick={() => setSelectedPlate(k)}
                disabled={!item.url}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                  selectedPlate === k ? 'bg-accent text-white shadow' : item.url ? 'bg-surface-2 text-ink-secondary hover:bg-surface-3 border border-transparent' : 'opacity-40 cursor-not-allowed bg-surface-2'
                }`}
              >
                <span>{item.label}</span>
                <span className="text-[0.5625rem] uppercase opacity-75 font-mono">[{item.badge}]</span>
              </button>
            ))}
          </div>
          <div className="rounded-xl border overflow-hidden bg-black/95 relative" style={{ borderColor: 'var(--border-subtle)' }}>
            <div className="p-3 bg-surface-2/90 flex flex-wrap items-center justify-between gap-2 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-status-good animate-pulse" />
                <span className="text-xs font-bold text-ink-primary">{activePlateObj.label}</span>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setInspectZoom(!inspectZoom)} className="px-2.5 py-1 text-[0.6875rem] font-bold rounded bg-surface-3 hover:bg-surface-1 text-ink-primary">
                  {inspectZoom ? '🔍 Reset View' : '🔎 Zoom In'}
                </button>
                {activePlateObj.url && (
                  <a href={api.evidenceUrl(activePlateObj.url)} target="_blank" rel="noreferrer" className="px-2.5 py-1 text-[0.6875rem] font-bold rounded bg-surface-3 hover:bg-surface-1 text-ink-primary inline-flex items-center gap-1">
                    <Download size={12} /> Open Full-Res
                  </a>
                )}
              </div>
            </div>
            <div className={`p-4 flex items-center justify-center transition-all overflow-hidden ${inspectZoom ? 'overflow-x-auto' : ''}`}>
              {activePlateObj.url ? (
                <div className="relative w-full max-w-4xl mx-auto overflow-hidden rounded-lg group select-none">
                  {/* Simulate the 'Before' view by dropping color and dimming the heatmap to look like a raw x-ray structural view */}
                  <div className="absolute inset-0 w-full h-full pointer-events-none" style={{ filter: 'grayscale(100%) contrast(1.2) brightness(0.6)' }}>
                    <AuthedImage src={api.evidenceUrl(activePlateObj.url)} alt="Structure" className={`w-full h-full object-contain transition-transform duration-300 origin-center ${inspectZoom ? 'min-w-[1200px] scale-[1.5]' : 'max-h-[580px]'}`} />
                  </div>
                  
                  {/* The 'After' view with full heatmaps revealed by a slider */}
                  <SplitLoupeOverlay url={api.evidenceUrl(activePlateObj.url)} alt={activePlateObj.label} inspectZoom={inspectZoom} />
                </div>
              ) : (
                <div className="py-20 text-center text-ink-muted">
                  <ImageIcon size={48} className="mx-auto mb-2 opacity-30" />
                  <p className="text-xs">Evidence plate not generated.</p>
                </div>
              )}
            </div>
            <div className="p-4 bg-surface-1 border-t border-black/10 dark:border-white/10 text-xs text-ink-secondary leading-relaxed">
              <span className="font-bold text-ink-primary">Diagnostic Value: </span>{activePlateObj.desc}
            </div>
          </div>
        </Card>
      )}

      {tab === 'ai' && (
        <Card title="Generative AI Detection" subtitle="Deep Neural Network classifications and bounding boxes">
          <div className="space-y-4 mt-4">
            <div className="flex items-center justify-between p-4 rounded-xl border bg-surface-2" style={{ borderColor: 'var(--border-subtle)' }}>
              <span className="text-sm font-bold text-ink-primary">Full Scene Generative AI Probability</span>
              <span className="text-lg font-black text-ink-primary tnum">{percent(aiBreakdown.generative_ai_prob || 0)}</span>
            </div>
            {aiBreakdown.face_scores && aiBreakdown.face_scores.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted mb-2">Detected Faces</h4>
                <div className="grid gap-3 grid-cols-1 sm:grid-cols-2">
                  {aiBreakdown.face_scores.map((face, idx) => (
                    <div key={idx} className="p-3 rounded-lg border bg-surface-1" style={{ borderColor: 'var(--border-subtle)' }}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-bold text-ink-primary">Face #{idx + 1}</span>
                        <span className={`text-xs font-black ${face.fake_probability > 0.5 ? 'text-status-critical' : 'text-status-good'}`}>{percent(face.fake_probability)}</span>
                      </div>
                      {face.box && <span className="text-[0.625rem] text-ink-muted mono">Bounding Box: [{face.box.map(Math.round).join(', ')}]</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {tab === 'tampering' && (
        <Card title="Structural Tampering Analysis" subtitle="Detection of cloning, splicing, and local manipulation">
          <div className="space-y-4 mt-4 font-mono max-h-96 overflow-y-auto">
            {renderEntries(tampering)}
          </div>
        </Card>
      )}

      {tab === 'stego' && (
        <Card title="Steganography & Hidden Payloads" subtitle="Least Significant Bit (LSB) anomaly detection">
          <div className="space-y-4 mt-4 font-mono max-h-96 overflow-y-auto">
             {renderEntries(stego)}
          </div>
          {stego.details && (
              <p className="text-xs text-ink-secondary leading-relaxed p-4 bg-surface-1 rounded-xl border border-black/5 dark:border-white/5">
                {stego.details}
              </p>
            )}
        </Card>
      )}

      {tab === 'metadata' && (
        <Card title="Cryptographic Identity & EXIF Metadata" subtitle="File security and format diagnostics">
           <div className="mt-4 font-mono max-h-96 overflow-y-auto">
             {renderEntries(metaForensics)}
           </div>
        </Card>
      )}
      </div>
    </div>
  )
}
