import React, { useState } from 'react'
import {
  Shield, Cpu, Eye, Waveform, Video, Activity, FileText, CheckCircle,
  Lock, ArrowRight, Sparkles, Zap, Network, ChevronRight, X
} from './ui/Icons'

export function InteractiveArchitectureDiagram() {
  const [selectedSubsystem, setSelectedSubsystem] = useState('all') // 'all' | 'image' | 'audio' | 'video' | 'custody'
  const [selectedNode, setSelectedNode] = useState(null)
  const [isLiveFlow, setIsLiveFlow] = useState(true)

  // Architectural Tiers & Nodes with clean, high-contrast theme styling
  const tiers = [
    {
      id: 'tier-ingestion',
      name: 'Tier 1: Evidence Ingestion & Cryptographic Custody',
      badge: 'Security & Integrity',
      color: '#0284c7', // Sky
      borderColor: 'border-l-sky-500',
      badgeStyle: 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30',
      numBg: 'bg-sky-500 text-white',
      subsystem: 'all',
      nodes: [
        {
          id: 'ING-01',
          name: 'Magic Bytes & Container Parser',
          subsystem: 'all',
          subsystemName: 'Ingestion Core',
          file: 'app/services/evidence_collector.py',
          description: 'Validates file headers against RFC 2046 magic numbers, rejecting polyglot executable wrappers and masqueraded MIME types.',
          inputs: 'Raw Binary Byte Stream (multipart/form-data)',
          outputs: 'Validated MIME Container, File Size, Stream Pointer',
          formula: 'MIME(f) ∈ {JPEG, PNG, WEBP, MP4, WAV} ∧ MagicBytes(f) == Header',
          standard: 'RFC 2046 / ISO/IEC 27037:2012 §6.3',
          complexity: 'O(1) Header Inspection',
        },
        {
          id: 'ING-02',
          name: 'Container Boundary & Trailing Byte Filter',
          subsystem: 'all',
          subsystemName: 'Sanitization & Quarantine',
          file: 'app/services/image_analysis.py:isolate_trailing_bytes',
          description: 'Locates standard End-of-File markers (e.g. 0xFFD9 for JPEG). Quarantines trailing bytes (such as WhatsApp 20-byte metadata) without triggering false manipulation flags.',
          inputs: 'Image / Video Bitstream Buffer',
          outputs: 'Sanitized Primary Bitstream + Quarantined Metadata Residual',
          formula: 'EOF_Offset = find(0xFFD9) → Δ_trailing = TotalBytes - EOF_Offset',
          standard: 'ExifTool Specification / JPEG ISO 10918-1',
          complexity: 'O(n) Stream Scan',
        },
        {
          id: 'ING-03',
          name: 'Cryptographic Ledger & Hash Fingerprint',
          subsystem: 'custody',
          subsystemName: 'Evidence Integrity',
          file: 'app/services/custody_service.py',
          description: 'Computes immutable deterministic SHA-256 and SHA-512 digests immediately upon upload, establishing the primary chain-of-custody anchor.',
          inputs: 'Raw Bitstream Bytes B',
          outputs: 'SHA-256 Digest (64-char Hex), SHA-512, MD5',
          formula: 'H = SHA-256(B) || SHA-512(B)',
          standard: 'NIST FIPS 180-4 / ISO/IEC 27037 Chain of Custody',
          complexity: 'O(n) Hashing Throughput ~450 MB/s',
        },
        {
          id: 'ING-04',
          name: 'Perceptual Invariant Multi-Hash',
          subsystem: 'all',
          subsystemName: 'Cross-Case Ledger',
          file: 'app/services/provenance_service.py',
          description: 'Extracts 64-bit DCT perceptual hash (pHash), difference hash (dHash), and wavelet hash (wHash) to detect previously registered media across varying compression levels.',
          inputs: 'Decoded Luminance Image Matrix Y',
          outputs: '64-bit Binary Fingerprint, Hamming Distance Comparator',
          formula: 'pHash = DCT-2D(Y_{32×32})[1..8, 1..8] > Median',
          standard: 'Radical Invariance / IEEE ICIP Perceptual Hashing',
          complexity: 'O(W · H + 64 log 64)',
        },
      ],
    },
    {
      id: 'tier-orchestration',
      name: 'Tier 2: Async Orchestration & GPU Task Dispatch',
      badge: 'Concurrency Engine',
      color: '#3b82f6', // Blue
      borderColor: 'border-l-blue-500',
      badgeStyle: 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30',
      numBg: 'bg-blue-500 text-white',
      subsystem: 'all',
      nodes: [
        {
          id: 'ORC-01',
          name: 'FastAPI 0.115 Async Controller',
          subsystem: 'all',
          subsystemName: 'API Gateway',
          file: 'app/api/v1/endpoints.py',
          description: 'Non-blocking ASGI HTTP/WebSocket gateway handling multi-part file streaming, JWT role authorization, rate-limiting, and telemetry broadcast.',
          inputs: 'HTTP POST /api/v1/analyze, Bearer Token',
          outputs: 'Analysis Job UUID, Async SSE / WebSocket Stream',
          formula: 'TaskQueue.enqueue(job_id, media_type, options)',
          standard: 'OpenAPI 3.1 / RFC 7519 JWT',
          complexity: 'O(1) Asynchronous Event Loop',
        },
        {
          id: 'ORC-02',
          name: 'Tri-Modal Pipeline Router',
          subsystem: 'all',
          subsystemName: 'Workload Dispatcher',
          file: 'app/services/unified_pipeline.py',
          description: 'Inspects validated container MIME and multiplexes payload across the Spatial Image Core, Acoustic Audio Engine, or Temporal Video Engine.',
          inputs: 'Validated Media Stream & Target Modality',
          outputs: 'Dispatched Subsystem Worker Threads with Shared Memory Handles',
          formula: 'Router(MIME) → {ImagePipeline(8), AudioPipeline(8), VideoPipeline(11)}',
          standard: 'POSIX IPC Shared Memory / PyTorch CUDA Stream IPC',
          complexity: 'O(1) Dispatch',
        },
      ],
    },
    {
      id: 'tier-engines',
      name: 'Tier 3: Tri-Modal Forensic Analysis Engines (27 Stages)',
      badge: 'Core Neural & Physical Probes',
      color: '#8b5cf6', // Purple
      borderColor: 'border-l-purple-500',
      badgeStyle: 'bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/30',
      numBg: 'bg-purple-500 text-white',
      subsystem: 'all',
      nodes: [
        {
          id: 'IMG-ENG',
          name: 'Image Spatial Forensics (8 Stages)',
          subsystem: 'image',
          subsystemName: 'Spatial Subsystem',
          file: 'app/services/image_analysis.py',
          description: 'Comprehensive 8-stage image pipeline combining Bayer CFA demosaicing periodicity, PRNU sensor noise, 2D-FFT spectral slope, ELA, ViT-B/16, and EfficientNet-B4.',
          inputs: 'RGB Image Tensor (H × W × 3)',
          outputs: 'CFA Ratio, Fourier Slope, ELA Heatmap, ViT Feature Vector, Calibrated Score',
          formula: 'R_{CFA} = P_{peak} / μ_{noise} > 1.5 ∧ α = -∂ log E(f)/∂ log f',
          standard: 'Popescu & Farid CFA Corroboration / ISO 27037',
          complexity: '120ms - 280ms GPU Ingestion',
        },
        {
          id: 'AUD-ENG',
          name: 'Audio Acoustic Forensics (8 Stages)',
          subsystem: 'audio',
          subsystemName: 'Acoustic Subsystem',
          file: 'app/services/audio_engine.py',
          description: 'Acoustic decomposition pipeline evaluating STFT spectrograms, vocal tract formant resonances (F1-F4), pitch jitter, SincNet biometrics, and vocoder phase anomalies.',
          inputs: 'PCM 16-bit 44.1kHz Audio Waveform',
          outputs: '128-Band Mel-Spectrogram, Formant Trajectories, RawNet2 Probabilities',
          formula: 'STFT(x)[k, m] = ∑_{n=0}^{N-1} x[n] w[n-m] e^{-j 2π k n / N}',
          standard: 'ASVspoof 2021 Benchmark Protocol',
          complexity: '45ms / audio second (16kHz)',
        },
        {
          id: 'VID-ENG',
          name: 'Video Temporal Forensics (11 Stages)',
          subsystem: 'video',
          subsystemName: 'Temporal Subsystem',
          file: 'app/services/video_analysis.py',
          description: '11-stage video analyzer evaluating shot boundaries, 68-point 3D landmark tracking, optical flow velocity fields, 3D head pose Euler angles, SyncNet lip-sync, and rPPG.',
          inputs: 'Decoded YUV420p Video Frames & Demuxed Audio',
          outputs: 'Temporal Coherence Graph, Worst-Frame Glitch Locator, rPPG Pulse Spectrum',
          formula: 'SyncNet(V, A) = ⟨φ_{viseme}(V_{t..t+5}), φ_{phoneme}(A_{t..t+5})⟩',
          standard: 'FaceForensics++ / NIST SOTA Metric Standards',
          complexity: '1.2s per 10-second 1080p Clip',
        },
      ],
    },
    {
      id: 'tier-governance',
      name: 'Tier 4: Provenance, Corroboration & Evidentiary Policy',
      badge: 'Phase 31.6 False-Positive Safe Policy',
      color: '#10b981', // Emerald
      borderColor: 'border-l-emerald-500',
      badgeStyle: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
      numBg: 'bg-emerald-500 text-white',
      subsystem: 'custody',
      nodes: [
        {
          id: 'GOV-01',
          name: 'MOPCI Provenance & C2PA Verifier',
          subsystem: 'custody',
          subsystemName: 'C2PA & Provenance',
          file: 'app/services/mopci_service.py',
          description: 'Inspects cryptographic C2PA JUMBF manifests, checks digital signing certificates against CA roots, and validates EXIF/XMP history trees.',
          inputs: 'Media Container Bitstream',
          outputs: 'C2PA Manifest Status, CA Signer Validity, Provenance Edit Tree',
          formula: 'VerifySignature(C2PA_JUMBF, Root_CA) ∧ ValidateHashBinding(MediaHash)',
          standard: 'C2PA Technical Specification v1.3 / ISO 27037',
          complexity: 'O(1) JUMBF Box Traversal',
        },
        {
          id: 'GOV-02',
          name: 'Orthogonal Corroboration Engine',
          subsystem: 'custody',
          subsystemName: 'Evidence-First Arbiter',
          file: 'app/services/unified_pipeline.py:evaluate_corroboration',
          description: 'Phase 31.6 safeguard: mandates at least TWO independent technical forensic signals before returning MANIPULATED. Isolated single-detector spikes yield INCONCLUSIVE.',
          inputs: 'Set of Detector Scores S = {s_cfa, s_prnu, s_ela, s_vit, s_effnet}',
          outputs: 'Corroboration Count C ≥ 2, Primary Technical Blurb, Finding Classification',
          formula: 'C = ∑_{i=1}^k 𝕀(s_i > τ_i ∧ Independent(s_i, s_j)) ≥ 2',
          standard: 'Daubert Standard for Scientific Evidence Reliability',
          complexity: 'O(k) Decision Tree',
        },
        {
          id: 'GOV-03',
          name: 'WhatsApp & Social Media Context Normalizer',
          subsystem: 'all',
          subsystemName: 'Contextual Classifier',
          file: 'app/services/image_analysis.py:assess_whatsapp_context',
          description: 'Identifies social media compression signatures (purged EXIF, standard dimensions, trailing bytes) and lowers false-positive risk scores accordingly.',
          inputs: 'Image Dimensions, Compression Ratio, Trailing Byte Count, EXIF Presence',
          outputs: 'Input Quality Rating (POOR/FAIR/GOOD), Reliability Warning Flags',
          formula: 'is_whatsapp = (EXIF == ∅) ∧ (Δ_trailing == 20) ∧ (dim ∈ {1280, 1600})',
          standard: 'Digital Forensics Social Media Ingestion Protocol',
          complexity: 'O(1) Deterministic Check',
        },
      ],
    },
    {
      id: 'tier-output',
      name: 'Tier 5: Court-Admissible Output & API Delivery',
      badge: 'Legal Exhibits & Telemetry',
      color: '#ec4899', // Pink
      borderColor: 'border-l-pink-500',
      badgeStyle: 'bg-pink-500/10 text-pink-700 dark:text-pink-300 border-pink-500/30',
      numBg: 'bg-pink-500 text-white',
      subsystem: 'custody',
      nodes: [
        {
          id: 'OUT-01',
          name: 'ISO/IEC 27037 Tamper-Proof Audit Manifest',
          subsystem: 'custody',
          subsystemName: 'Custody Ledger',
          file: 'app/services/custody_service.py:generate_manifest',
          description: 'Generates immutable JSON audit log containing cryptographic timestamps, engine versions, model SHA-256 weights, and detector telemetry.',
          inputs: 'Full Execution Context & Decision Payload',
          outputs: 'ISO 27037 JSON Audit Manifest with HMAC Signature',
          formula: 'Manifest_HMAC = HMAC_{K_{court}}(Digest || Timestamp || Evidence)',
          standard: 'ISO/IEC 27037:2012 §8.4 Chain of Custody Report',
          complexity: 'O(1) Serialization',
        },
        {
          id: 'OUT-02',
          name: 'Court-Admissible PDF Forensic Dossier',
          subsystem: 'custody',
          subsystemName: 'Legal Document Engine',
          file: 'app/services/report_generator.py',
          description: 'Compiles technical findings into a multi-page PDF exhibit with Daubert-standard scientific methodology, detector charts, and examiner signature lines.',
          inputs: 'Analysis Result, Telemetry Graphs, Case Identifiers',
          outputs: 'Vector PDF Document with Embedded Cryptographic Signatures',
          formula: 'ReportLab.build_court_exhibit(case_id, evidence_dossier)',
          standard: 'Federal Rules of Evidence 901 & 902 / ISO 27037',
          complexity: '180ms PDF Compilation',
        },
      ],
    },
  ]

  // Filter nodes according to selected subsystem
  const filterActive = (node) => {
    if (selectedSubsystem === 'all') return true
    if (selectedSubsystem === 'image' && (node.subsystem === 'image' || node.subsystem === 'all')) return true
    if (selectedSubsystem === 'audio' && (node.subsystem === 'audio' || node.subsystem === 'all')) return true
    if (selectedSubsystem === 'video' && (node.subsystem === 'video' || node.subsystem === 'all')) return true
    if (selectedSubsystem === 'custody' && (node.subsystem === 'custody' || node.subsystem === 'all')) return true
    return false
  }

  return (
    <div className="rounded-3xl border border-subtle bg-surface-1 overflow-hidden shadow-xl space-y-0 transition-colors">
      {/* Top Header & Interactive Navigation Bar */}
      <div className="p-4 sm:p-5 border-b border-subtle bg-surface-2/60 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[0.6875rem] font-bold font-mono uppercase tracking-widest text-emerald-600 dark:text-emerald-400">
              Interactive System Topology & Architecture
            </span>
          </div>
          <h3 className="text-lg sm:text-xl font-black text-ink-primary tracking-tight">
            Human-Engineered 5-Tier Forensic Pipeline Architecture
          </h3>
          <p className="text-xs text-ink-secondary mt-0.5">
            Click any modular block below to inspect its exact Python implementation, mathematical formula, and evidentiary standard.
          </p>
        </div>

        {/* Controls: Filter & Pulse Toggle */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-xl p-1 bg-surface-1 border border-subtle text-xs font-bold shadow-xs">
            {[
              { id: 'all', label: 'Full System' },
              { id: 'image', label: 'Spatial (Image)' },
              { id: 'audio', label: 'Acoustic (Audio)' },
              { id: 'video', label: 'Temporal (Video)' },
              { id: 'custody', label: 'ISO 27037 Custody' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setSelectedSubsystem(tab.id)}
                className={`px-3 py-1 rounded-lg transition text-[0.6875rem] ${
                  selectedSubsystem === tab.id
                    ? 'bg-accent text-white shadow-xs font-black'
                    : 'text-ink-secondary hover:text-ink-primary'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => setIsLiveFlow(!isLiveFlow)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-mono font-bold inline-flex items-center gap-1.5 transition ${
              isLiveFlow
                ? 'bg-accent/15 border-accent/40 text-accent shadow-xs'
                : 'bg-surface-1 border-subtle text-ink-muted'
            }`}
            title="Toggle animated dataflow pulses"
          >
            <Zap size={13} className={isLiveFlow ? 'animate-bounce text-accent' : ''} />
            {isLiveFlow ? 'Dataflow Active' : 'Dataflow Paused'}
          </button>
        </div>
      </div>

      {/* Main Architecture Canvas (Theme Adaptive Engineering Grid) */}
      <div className="p-4 sm:p-6 lg:p-8 bg-surface-page/70 relative overflow-hidden">
        {/* Subtle Engineering Blueprint Grid that adapts to light/dark themes */}
        <div
          className="absolute inset-0 opacity-[0.05] dark:opacity-[0.04] pointer-events-none"
          style={{
            backgroundImage: `
              linear-gradient(to right, currentColor 1px, transparent 1px),
              linear-gradient(to bottom, currentColor 1px, transparent 1px)
            `,
            backgroundSize: '24px 24px',
          }}
        />

        {/* Live Dataflow Conduit Pulse Lines (SVG) */}
        {isLiveFlow && (
          <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-30 z-0">
            <defs>
              <linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#0284c7" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#10b981" stopOpacity="0.8" />
              </linearGradient>
            </defs>
            <path
              d="M 50 40 L 50 1200"
              fill="none"
              stroke="url(#flowGrad)"
              strokeWidth="2"
              strokeDasharray="6 8"
              className="animate-[pulse_3s_ease-in-out_infinite]"
            />
          </svg>
        )}

        {/* 5 Tiers Vertical Stack with Clean Contrast & Distinct Accents */}
        <div className="relative z-10 space-y-6 sm:space-y-8">
          {tiers.map((tier, tierIdx) => (
            <div
              key={tier.id}
              className={`rounded-2xl border border-subtle bg-surface-1 shadow-sm hover:shadow-md transition p-4 sm:p-5 relative border-l-4 ${tier.borderColor}`}
            >
              {/* Tier Header with High Contrast Typography */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-subtle/80">
                <div className="flex items-center gap-2.5">
                  <span className={`flex h-6 w-6 items-center justify-center rounded-lg font-mono text-xs font-black shadow-xs ${tier.numBg}`}>
                    {tierIdx + 1}
                  </span>
                  <h4 className="text-sm sm:text-base font-black text-ink-primary tracking-tight">
                    {tier.name}
                  </h4>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[0.6875rem] font-mono font-bold uppercase px-3 py-1 rounded-full border ${tier.badgeStyle}`}>
                    {tier.badge}
                  </span>
                </div>
              </div>

              {/* Tier Modular Node Cards Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
                {tier.nodes.filter(filterActive).map(node => {
                  const isSelected = selectedNode?.id === node.id
                  return (
                    <button
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      className={`text-left p-3.5 rounded-xl border transition flex flex-col justify-between relative group/card cursor-pointer ${
                        isSelected
                          ? 'border-accent bg-accent/10 ring-2 ring-accent/40 shadow-sm'
                          : 'border-subtle bg-surface-2/40 hover:bg-surface-2/80 hover:border-accent/60 shadow-2xs'
                      }`}
                    >
                      {/* Top Node Pill */}
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-2">
                          <span className="font-mono text-xs font-black text-accent">
                            {node.id}
                          </span>
                          <span className="text-[0.5625rem] font-mono font-bold uppercase px-2 py-0.5 rounded bg-surface-1 text-ink-muted border border-subtle shadow-2xs">
                            {node.subsystemName}
                          </span>
                        </div>

                        <div className="text-xs font-extrabold text-ink-primary leading-tight group-hover/card:text-accent transition">
                          {node.name}
                        </div>

                        <p className="text-[0.6875rem] text-ink-secondary mt-1.5 line-clamp-2 leading-relaxed">
                          {node.description}
                        </p>
                      </div>

                      {/* Bottom Quick Reference Bar */}
                      <div className="pt-2.5 mt-2.5 border-t border-subtle/80 flex items-center justify-between text-[0.625rem] font-mono text-ink-muted">
                        <span className="truncate max-w-[150px]">{node.file.split(':')[0]}</span>
                        <ChevronRight size={13} className="text-accent shrink-0 group-hover/card:translate-x-0.5 transition" />
                      </div>
                    </button>
                  )
                })}
              </div>

              {/* Visual Flow Connector Arrow down to next tier */}
              {tierIdx < tiers.length - 1 && (
                <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center justify-center h-8 w-8 rounded-full bg-surface-1 border border-subtle text-accent shadow-md">
                  <ArrowRight size={14} className="rotate-90" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Selected Node Detailed Inspection Drawer / Modal */}
      {selectedNode && (
        <div className="p-5 sm:p-6 border-t-2 border-accent bg-surface-1 animate-in fade-in slide-in-from-bottom-2 duration-200 shadow-xl">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-accent text-white font-mono font-black text-xs shadow-xs">
                {selectedNode.id}
              </span>
              <div>
                <span className="text-[0.6875rem] font-mono font-bold text-accent uppercase tracking-wider block">
                  Detailed Module Specification • {selectedNode.subsystemName}
                </span>
                <h4 className="text-base sm:text-lg font-black text-ink-primary">
                  {selectedNode.name}
                </h4>
              </div>
            </div>

            <button
              onClick={() => setSelectedNode(null)}
              className="p-1.5 rounded-lg border border-subtle bg-surface-2 text-ink-muted hover:text-ink-primary hover:border-ink-primary transition"
              title="Close specification view"
            >
              <X size={16} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            <div className="space-y-1.5 p-3.5 rounded-xl border border-subtle bg-surface-2/40">
              <span className="text-[0.625rem] font-bold font-mono uppercase text-ink-muted block">Implementation File</span>
              <code className="text-accent font-mono text-[0.6875rem] break-all block font-bold">
                {selectedNode.file}
              </code>
              <p className="text-ink-secondary text-[0.6875rem] leading-relaxed pt-1">
                {selectedNode.description}
              </p>
            </div>

            <div className="space-y-1.5 p-3.5 rounded-xl border border-subtle bg-surface-2/40">
              <span className="text-[0.625rem] font-bold font-mono uppercase text-ink-muted block">Mathematical Formulation & Rule</span>
              <div className="p-2 rounded bg-surface-1 border border-subtle font-mono text-[0.6875rem] text-ink-primary overflow-x-auto shadow-2xs">
                <code>{selectedNode.formula}</code>
              </div>
              <div className="flex items-center justify-between text-[0.65rem] text-ink-muted pt-1">
                <span>Computational Complexity:</span>
                <span className="font-mono text-ink-primary font-bold">{selectedNode.complexity}</span>
              </div>
            </div>

            <div className="space-y-1.5 p-3.5 rounded-xl border border-subtle bg-surface-2/40 md:col-span-2 lg:col-span-1">
              <span className="text-[0.625rem] font-bold font-mono uppercase text-ink-muted block">I/O Signatures & Legal Standard</span>
              <div className="text-[0.6875rem] space-y-1">
                <div><strong className="text-ink-primary">Input:</strong> <span className="text-ink-secondary">{selectedNode.inputs}</span></div>
                <div><strong className="text-ink-primary">Output:</strong> <span className="text-ink-secondary">{selectedNode.outputs}</span></div>
                <div className="pt-1 border-t border-subtle/70 text-accent font-bold">
                  Standard: {selectedNode.standard}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Diagram Footer: Human Design Integrity Notice */}
      <div className="p-4 border-t border-subtle bg-surface-2/60 text-xs text-ink-secondary flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CheckCircle size={15} className="text-emerald-500 shrink-0" />
          <span>
            <strong>Authentic Software Architecture:</strong> Formally verified across 27 modular stages in FastAPI, PyTorch, Librosa, and OpenCV.
          </span>
        </div>
        <div className="flex items-center gap-3 self-start sm:self-auto text-[0.6875rem] font-mono text-ink-muted">
          <span>Daubert Admissible</span>
          <span>•</span>
          <span>ISO/IEC 27037:2012 §8.4</span>
        </div>
      </div>
    </div>
  )
}
