import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Notice, Badge } from '../components/ui'
import {
  Activity, CheckCircle, Cpu, FileText, Sparkles, Upload, Clock, Info,
  AlertTriangle, Hash, Globe, Search, Zap, Shield, ShieldCheck, ShieldAlert,
  ShieldQuestion, Eye, Download, Check, Alert, Waveform, Video as VideoIcon,
  Image as ImageIcon, GitBranch, Network, ExternalLink
} from '../components/ui/Icons'
import { api } from '../lib/api'
import { InteractiveArchitectureDiagram } from '../components/InteractiveArchitectureDiagram'
import { ForensicDiagnosticWorkbench } from '../components/ForensicDiagnosticWorkbench'

export default function HowItWorks() {
  const [health, setHealth] = useState(null)
  const [activeTab, setActiveTab] = useState('image')
  const [activeSection, setActiveSection] = useState('overview')

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])

  const scrollTo = (id) => {
    setActiveSection(id)
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <div className="mx-auto max-w-[1400px] animate-in space-y-12 pb-24 px-4 sm:px-6">
      
      {/* ── STICKY QUICK-NAVIGATION JUMP BAR ──────────────────────────────── */}
      <div className="sticky top-16 z-20 backdrop-blur-xl border-y py-2.5 px-4 -mx-4 sm:mx-0 sm:rounded-2xl border-subtle bg-surface-1/90 shadow-md flex items-center justify-between overflow-x-auto gap-2 text-xs">
        <span className="font-mono font-bold text-accent uppercase text-[0.6875rem] tracking-wider shrink-0 flex items-center gap-1.5">
          <Zap size={13} /> Navigation:
        </span>
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          {[
            { id: 'overview', label: 'Architecture Overview' },
            { id: 'flow-diagram', label: 'System Topology' },
            { id: 'laboratory-workbench', label: 'Diagnostic Workbench' },
            { id: 'image-pipeline', label: 'Image Forensics (8 Stages)' },
            { id: 'audio-pipeline', label: 'Audio Engine (8 Stages)' },
            { id: 'video-pipeline', label: 'Video Engine (11 Stages)' },
            { id: 'mopci', label: 'MOPCI Provenance' },
            { id: 'false-positive-safe', label: 'Evidence-First Policy' },
            { id: 'chain-of-custody', label: 'Chain of Custody' },
            { id: 'telemetry', label: 'Live Telemetry' },
            { id: 'limitations', label: 'Scientific Rigor' },
          ].map(item => (
            <button
              key={item.id}
              onClick={() => scrollTo(item.id)}
              className={`px-3 py-1 rounded-lg font-semibold transition whitespace-nowrap text-[0.75rem] ${
                activeSection === item.id
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'text-ink-secondary hover:text-ink-primary hover:bg-surface-2'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── HERO BANNER ───────────────────────────────────────────────────── */}
      <section id="overview" className="relative rounded-3xl border border-subtle overflow-hidden p-8 sm:p-12 bg-surface-2">
        <div className="pointer-events-none absolute inset-0 opacity-[0.05]"
             style={{ background: 'radial-gradient(circle at 70% 30%, var(--accent), transparent 60%)' }} />
        
        <div className="max-w-4xl space-y-4 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/30 bg-accent/10 text-accent text-[0.6875rem] font-bold uppercase tracking-widest">
            <Sparkles size={13} />
            Phase 31.6 Technical Specification • Multi-Modal Deepfake Forensics
          </div>
          
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-ink-primary" style={{ letterSpacing: '-0.04em' }}>
            Inside the Veritas Multi-Modal Forensic Engine
          </h1>
          
          <p className="text-base sm:text-lg text-ink-secondary leading-relaxed max-w-3xl">
            A comprehensive, court-ready digital forensics platform engineering 27 modular stages across spatial, acoustic, temporal, and cryptographic dimensions. Designed under strict evidentiary principles where raw neural scores are rigorously separated from final forensic determinations.
          </p>

          {/* Quick Platform Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4">
            <div className="p-3.5 rounded-2xl border border-subtle bg-surface-1">
              <span className="text-[0.65rem] font-black uppercase tracking-wider text-ink-muted block">Modular Pipeline</span>
              <span className="text-2xl font-black font-mono text-accent mt-0.5 block">27 Stages</span>
              <span className="text-[0.6875rem] text-ink-muted">8 Image • 8 Audio • 11 Video</span>
            </div>
            <div className="p-3.5 rounded-2xl border border-subtle bg-surface-1">
              <span className="text-[0.65rem] font-black uppercase tracking-wider text-ink-muted block">Neural & Signal Ensembles</span>
              <span className="text-2xl font-black font-mono text-ink-primary mt-0.5 block">15+ Models</span>
              <span className="text-[0.6875rem] text-ink-muted">ViT, EfficientNet, RawNet, LCNN</span>
            </div>
            <div className="p-3.5 rounded-2xl border border-subtle bg-surface-1">
              <span className="text-[0.65rem] font-black uppercase tracking-wider text-ink-muted block">Evidentiary Safety</span>
              <span className="text-2xl font-black font-mono text-emerald-400 mt-0.5 block">Zero Bias</span>
              <span className="text-[0.6875rem] text-ink-muted">WhatsApp/Messaging Safe UX</span>
            </div>
            <div className="p-3.5 rounded-2xl border border-subtle bg-surface-1">
              <span className="text-[0.65rem] font-black uppercase tracking-wider text-ink-muted block">Legal Standards</span>
              <span className="text-2xl font-black font-mono text-ink-primary mt-0.5 block">ISO 27037</span>
              <span className="text-[0.6875rem] text-ink-muted">Immutable SHA-256 Ledger</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 1: MASTER ARCHITECTURE & END-TO-END SYSTEM FLOW ───────── */}
      <section id="flow-diagram" className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <span className="text-[0.6875rem] font-black uppercase tracking-widest text-accent">System Architecture</span>
            <h2 className="text-2xl sm:text-3xl font-black text-ink-primary tracking-tight">End-to-End Forensic Workflow</h2>
          </div>
          <p className="text-xs text-ink-muted max-w-md">
            From secure byte ingestion and polyglot container inspection to calibrated orthogonal evidence fusion and court-ready PDF generation.
          </p>
        </div>

        {/* Master Interactive Architecture Diagram (Human-Engineered 5-Tier Topology) */}
        <InteractiveArchitectureDiagram />

        {/* Detailed 6-Step Interactive Flow Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              step: '01',
              title: 'Secure Ingestion & Validation',
              desc: 'Enforces strict MIME validation, magic-byte parsing, container structural integrity, and trailing data isolation to prevent polyglot injection.',
              tag: 'Security & I/O',
            },
            {
              step: '02',
              title: 'Cryptographic Ledgering',
              desc: 'Calculates deterministic digests: SHA-256, SHA-512, MD5, and multi-dimensional perceptual hashes (pHash, dHash, aHash, wHash) for chain of custody.',
              tag: 'Chain of Custody',
            },
            {
              step: '03',
              title: 'Physical & Frequency Decomposition',
              desc: 'Extracts Bayer CFA demosaicing periodicity, PRNU sensor noise residuals, 2D-DCT spectral slopes, and Error Level Analysis (ELA) compression differentials.',
              tag: 'Signal Forensics',
            },
            {
              step: '04',
              title: 'Multi-Backbone Neural Probe',
              desc: 'Runs specialized vision transformers, EfficientNet biometric classifiers, RawNet acoustic networks, and SyncNet temporal lip-sync trackers.',
              tag: 'Deep Learning',
            },
            {
              step: '05',
              title: 'MOPCI Provenance & Source Discovery',
              desc: 'Inspects C2PA Content Credentials, executes reverse media search across historical registries, and assesses 3D physical world consistency.',
              tag: 'Provenance & OSINT',
            },
            {
              step: '06',
              title: 'Calibrated Evidence Fusion',
              desc: 'Evaluates orthogonal signal counts and applies Phase 17.8R logistic calibration, guaranteeing that isolated model scores never force false verdicts.',
              tag: 'Decision Policy',
            },
          ].map(s => (
            <div key={s.step} className="p-5 rounded-2xl border border-subtle bg-surface-1 flex flex-col justify-between hover:border-accent transition group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-xl font-black text-accent">{s.step}</span>
                  <span className="text-[0.625rem] font-bold font-mono uppercase px-2 py-0.5 rounded bg-surface-2 border border-subtle text-ink-secondary">
                    {s.tag}
                  </span>
                </div>
                <h3 className="text-base font-extrabold text-ink-primary mb-2 group-hover:text-accent transition">
                  {s.title}
                </h3>
                <p className="text-xs text-ink-secondary leading-relaxed">
                  {s.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 2: INTERACTIVE FORENSIC DIAGNOSTIC WORKBENCH ───────────── */}
      <section id="laboratory-workbench" className="space-y-6">
        <ForensicDiagnosticWorkbench />
      </section>

      {/* ── SECTION 3: IMAGE FORENSICS PIPELINE (8 STAGES) ────────────────── */}
      <section id="image-pipeline" className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <span className="text-[0.6875rem] font-black uppercase tracking-widest text-[#00E5FF]">Spatial Architecture</span>
            <h2 className="text-2xl sm:text-3xl font-black text-ink-primary tracking-tight">8-Stage Image Forensics Pipeline</h2>
          </div>
          <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-surface-2 border border-subtle text-ink-secondary">
            Image Ingestion → Calibrated Report
          </span>
        </div>

        <div className="space-y-3.5">
          {[
            {
              stage: 1,
              name: 'Secure Ingestion & Validation',
              category: 'File Ingestion',
              math: 'MIME(f) \\in \\{JPEG, PNG, WEBP\\} \\land \\text{MagicBytes}(f)',
              summary: 'Inspects header signatures, MIME types, byte stream dimensions, and checks for trailing bytes or polyglot files.',
              forensicDepth: 'Prevents adversarial payloads from masquerading as image files. Isolates hidden appended bytes after the End-of-File (EOF) marker (e.g. 20 trailing bytes frequently appended by mobile messaging applications like WhatsApp).',
            },
            {
              stage: 2,
              name: 'File Container & Cryptographic Ledger',
              category: 'File Forensics',
              math: 'H = \\text{SHA-256}(B) \\parallel \\text{pHash}(I, 64)',
              summary: 'Generates immutable cryptographic digests and robust perceptual hashes.',
              forensicDepth: 'Establishes chain of custody. Perceptual hashes (pHash, dHash, aHash, wHash) preserve invariant geometric feature frequencies, allowing the system to track whether this image has been previously analyzed under different filenames or mild compression.',
            },
            {
              stage: 3,
              name: 'Metadata & Digital Timeline Forensics',
              category: 'Provenance & Metadata',
              math: '\\Delta t = t_{\\text{capture}} - t_{\\text{modified}} \\land \\text{EXIF}(\\text{CameraModel})',
              summary: 'Parses TIFF/EXIF structures, maker notes, software signatures, GPS geotags, and timeline consistency.',
              forensicDepth: 'Detects PURGED_METADATA. Explains that social-media platforms systematically strip EXIF tags. A lack of metadata is recorded as provenance limitation, never as proof of AI generation.',
            },
            {
              stage: 4,
              name: 'Frequency & Physical Signal Forensics',
              category: 'Physical Signal Analysis',
              math: 'R_{\\text{CFA}} = \\frac{P_{\\text{peak}}}{\\mu_{\\text{noise}}} > 1.5 \\land \\alpha = -\\frac{\\partial \\log E(f)}{\\partial \\log f}',
              summary: 'Calculates Bayer Color Filter Array (CFA) demosaicing periodicity, Fourier spectral slopes, Wavelet HH noise variance, and ELA.',
              forensicDepth: 'Physical silicon sensors utilize a physical color filter array that imparts periodic demosaicing correlations. Synthetic generative models render RGB pixels without optical CFA patterns. Real cameras yield CFA periodicity ratio > 1.5 and sensor noise standard deviation > 4.5.',
            },
            {
              stage: 5,
              name: 'Tampering, Splicing & Watermark Engine',
              category: 'Manipulation Detection',
              math: '\\mathcal{D}_{\\text{ELA}} = |I - \\mathcal{Q}_{90}(I)| \\land \\text{SIFT/ORB Clone Clusters}',
              summary: 'Error Level Analysis (ELA), keypoint cloning clusters, and digital boundary splicing gradient detection.',
              forensicDepth: 'Differential compression error mapping highlights localized regions saved at different quantization tables. Identifies digital cut-and-paste forgery, cloned objects, and composite inpainting.',
            },
            {
              stage: 6,
              name: 'AI & Deepfake Neural Detection Ensemble',
              category: 'Deep Learning Ensemble',
              math: 'P_{\\text{raw}} = w_1 P_{\\text{ViT}}(I) + w_2 P_{\\text{EffNet}}(F) + w_3 P_{\\text{SDXL}}(I)',
              summary: 'Multi-backbone neural evaluation using Vision Transformers (ViT), EfficientNet-B4 biometric classifiers, and SDXL probes.',
              forensicDepth: 'Evaluates latent diffusion synthetic artifacts and facial landmark blending. Raw scores are exposed transparently as individual probe telemetry, strictly decoupled from final systemic verdicts.',
            },
            {
              stage: 7,
              name: 'Steganography & Threat IOC Extraction',
              category: 'Cyber Forensics',
              math: '\\mathcal{H}_{\\text{LSB}} = -\\sum_{i=0}^1 p_i \\log_2(p_i) \\land \\text{IOC}(\\text{Signatures})',
              summary: 'LSB bitplane entropy analysis, hidden message payload estimation, and cyber threat indicators of compromise.',
              forensicDepth: 'Measures high-frequency randomized bitplane entropy across color channels to detect covert steganographic exfiltration or covert neural model watermarks.',
            },
            {
              stage: 8,
              name: 'Evidence Fusion & Calibrated Risk Engine',
              category: 'Synthesis & Decision Policy',
              math: 'z = \\beta_0 + \\sum_{i=1}^k \\beta_i x_i \\implies P_{\\text{fused}} = \\frac{1}{1 + e^{-z}}',
              summary: 'Phase 17.8R logistic evidence fusion, orthogonal corroboration counting, and false-positive safe calibration.',
              forensicDepth: 'Considers signal consensus. If only 1 neural detector fires while physical CFA demosaicing and facial biometrics indicate natural optical capture, the engine classifies the event as an ISOLATED_ANOMALY and issues an INCONCLUSIVE finding.',
            },
          ].map(s => (
            <div key={s.stage} className="p-5 rounded-2xl border border-subtle bg-surface-1 hover:border-accent transition">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/15 text-accent text-xs font-black font-mono">
                    {s.stage}
                  </span>
                  <h3 className="text-base font-extrabold text-ink-primary">{s.name}</h3>
                </div>
                <span className="text-[0.625rem] font-bold font-mono uppercase px-2 py-0.5 rounded bg-surface-2 text-ink-secondary border border-subtle">
                  {s.category}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-surface-2 border border-subtle font-mono text-xs text-accent mb-3 overflow-x-auto">
                <code>{s.math}</code>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs leading-relaxed">
                <div>
                  <span className="font-bold text-ink-muted uppercase text-[0.65rem] block mb-1">Functional Summary</span>
                  <p className="text-ink-secondary">{s.summary}</p>
                </div>
                <div>
                  <span className="font-bold text-accent uppercase text-[0.65rem] block mb-1">Forensic Significance</span>
                  <p className="text-ink-secondary">{s.forensicDepth}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 4: AUDIO FORENSICS PIPELINE (8 STAGES) ────────────────── */}
      <section id="audio-pipeline" className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <span className="text-[0.6875rem] font-black uppercase tracking-widest text-[#00E5FF]">Acoustic Architecture</span>
            <h2 className="text-2xl sm:text-3xl font-black text-ink-primary tracking-tight">8-Stage Acoustic Forensics Engine</h2>
          </div>
          <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-surface-2 border border-subtle text-ink-secondary">
            Voice Forensics • Speech Synthesis Detection
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              stage: 1,
              name: 'Ingestion & 16kHz Normalization',
              desc: 'Decodes WAV, MP3, AAC, FLAC bitstreams. Normalizes to 16,000 Hz 16-bit mono PCM to prevent sample rate artifact bias.',
            },
            {
              stage: 2,
              name: 'LFCC & CQT Scalogram Transform',
              desc: 'Linear Frequency Cepstral Coefficients (LFCC) capture high-frequency filter-bank phase anomalies characteristic of neural vocoders.',
            },
            {
              stage: 3,
              name: 'Neural Voice Classifier Ensemble',
              desc: 'Evaluates audio segments using RawNet2, LCNN (Light-CNN), and WavLM self-supervised speech representations to detect cloned TTS.',
            },
            {
              stage: 4,
              name: 'Glottal Pulse & Vocal Biomechanics',
              desc: 'Models natural human vocal cord glottal flow waveforms. Synthetic vocoders struggle to simulate non-linear human mucosal wave physics.',
            },
            {
              stage: 5,
              name: 'Speech Semantics, Jitter & Shimmer',
              desc: 'Quantifies pitch period perturbations (jitter) and amplitude variations (shimmer). AI voices exhibit unnaturally low micro-tremors.',
            },
            {
              stage: 6,
              name: 'Electrical Network Frequency (ENF)',
              desc: 'Extracts 50 Hz / 60 Hz power grid hum embedded in analog recording circuitry to verify geographic recording location and time.',
            },
            {
              stage: 7,
              name: 'Acoustic Splicing & Edit Boundary Localization',
              desc: 'Detects phase discontinuities, abrupt room impulse response (RIR) shifts, and high-frequency spectral edit cuts.',
            },
            {
              stage: 8,
              name: 'Calibrated Likelihood Ratio (LR)',
              desc: 'Produces calibrated forensic likelihood ratios and conformal prediction sets in accordance with forensic speaker recognition standards.',
            },
          ].map(s => (
            <div key={s.stage} className="p-5 rounded-2xl border border-subtle bg-surface-1 space-y-2 hover:border-accent transition">
              <div className="flex items-center gap-2">
                <span className="h-5 w-5 rounded-full bg-accent/15 text-accent text-xs font-black font-mono flex items-center justify-center">
                  {s.stage}
                </span>
                <h3 className="text-sm font-extrabold text-ink-primary">{s.name}</h3>
              </div>
              <p className="text-xs text-ink-secondary leading-relaxed pl-7">
                {s.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 5: VIDEO FORENSICS PIPELINE (11 STAGES) ───────────────── */}
      <section id="video-pipeline" className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <span className="text-[0.6875rem] font-black uppercase tracking-widest text-[#00E5FF]">Temporal Architecture</span>
            <h2 className="text-2xl sm:text-3xl font-black text-ink-primary tracking-tight">11-Stage Sequential Video Engine</h2>
          </div>
          <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-surface-2 border border-subtle text-ink-secondary">
            Temporal Coherence • Facial Swapping • AV Sync
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {[
            { stage: 1, name: 'Container & Bitstream Forensics', desc: 'Inspects MP4/MKV atom structures, GOP (Group of Pictures) cadence, and codec re-encoding tags.' },
            { stage: 2, name: 'Shot Boundary & Scene Segmentation', desc: 'Detects cut transitions, dissolves, and camera motion changes to segment analysis units.' },
            { stage: 3, name: 'Facial Landmark Tracking', desc: 'Tracks 68 3D facial landmarks across frames, isolating boundary blending and warp seams.' },
            { stage: 4, name: 'Inter-Frame Coherence & Flicker', desc: 'Computes frame-to-frame pixel residual flicker and high-frequency temporal noise inconsistency.' },
            { stage: 5, name: 'Optical Flow Motion Vectors', desc: 'Extracts dense Lucas-Kanade / Farnebäck optical flow fields to detect motion vector decoupling.' },
            { stage: 6, name: '3D Head Pose & Perspective Consistency', desc: 'Models 3D rotational yaw, pitch, and roll to detect impossible head-neck angle dislocations.' },
            { stage: 7, name: 'Audio-Visual Lip-Sync (SyncNet)', desc: 'Calculates cross-modal phoneme-viseme temporal correlation between speech formants and mouth shape.' },
            { stage: 8, name: 'Physiological Biometrics (rPPG)', desc: 'Remote Photoplethysmography: extracts cardiac blood volume pulse signals from facial skin chromaticity.' },
            { stage: 9, name: 'Worst-Frame Anomaly Localization', desc: 'Isolates and highlights individual anomalous frames containing momentary face-swap glitch artifacts.' },
            { stage: 10, name: 'Temporal Score Aggregation', desc: 'Aggregates multi-frame probabilities with attention-weighted confidence and outlier rejection.' },
            { stage: 11, name: 'Unified Video Forensic Synthesis', desc: 'Synthesizes visual, acoustic, and temporal metrics into a calibrated multimodal dossier.' },
          ].map(s => (
            <div key={s.stage} className="p-4 rounded-xl border border-subtle bg-surface-1 hover:border-accent transition space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="h-5 w-5 rounded-full bg-accent/15 text-accent text-xs font-black font-mono flex items-center justify-center">
                  {s.stage}
                </span>
                <h4 className="text-xs font-bold text-ink-primary truncate">{s.name}</h4>
              </div>
              <p className="text-[0.6875rem] text-ink-secondary leading-relaxed pl-7">
                {s.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 6: MOPCI PROVENANCE & SOURCE DISCOVERY ────────────────── */}
      <section id="mopci" className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <span className="text-[0.6875rem] font-black uppercase tracking-widest text-[#00E5FF]">Origin & Intelligence</span>
            <h2 className="text-2xl sm:text-3xl font-black text-ink-primary tracking-tight">MOPCI: Media Origin, Provenance & Content Intelligence</h2>
          </div>
          <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-surface-2 border border-subtle text-ink-secondary">
            C2PA • Genealogy • Reverse Search
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-6 rounded-2xl border border-subtle bg-surface-1 space-y-3">
            <div className="flex items-center gap-2.5 text-accent">
              <ShieldCheck size={20} />
              <h3 className="text-base font-extrabold text-ink-primary">1. C2PA Cryptographic Content Credentials</h3>
            </div>
            <p className="text-xs text-ink-secondary leading-relaxed">
              Parses Coalition for Content Provenance and Authenticity (C2PA) manifests embedded in file headers. Validates X.509 digital signing certificates, claims bindings, and editing history assertions.
            </p>
            <div className="p-3 rounded-xl bg-surface-2 border border-subtle text-[0.6875rem] text-ink-muted">
              <strong>Forensic Principle:</strong> Absence of C2PA credentials is standard across consumer devices and messaging apps; absence is never interpreted as proof of AI generation.
            </div>
          </div>

          <div className="p-6 rounded-2xl border border-subtle bg-surface-1 space-y-3">
            <div className="flex items-center gap-2.5 text-accent">
              <Search size={20} />
              <h3 className="text-base font-extrabold text-ink-primary">2. Reverse Media Search & Source Candidate Discovery</h3>
            </div>
            <p className="text-xs text-ink-secondary leading-relaxed">
              Computes invariant perceptual hashes (pHash, dHash) to match against media registries and web indexes to identify earliest known occurrences, re-encodings, or original unmodified candidates.
            </p>
            <div className="p-3 rounded-xl bg-surface-2 border border-subtle text-[0.6875rem] text-ink-muted">
              <strong>Candidate vs Source:</strong> Discovered web occurrences are designated <em>Source Candidates</em>, never original sources unless verified cryptographically.
            </div>
          </div>

          <div className="p-6 rounded-2xl border border-subtle bg-surface-1 space-y-3">
            <div className="flex items-center gap-2.5 text-accent">
              <Cpu size={20} />
              <h3 className="text-base font-extrabold text-ink-primary">3. Generative Model Family Attribution</h3>
            </div>
            <p className="text-xs text-ink-secondary leading-relaxed">
              Analyzes latent architectural fingerprints to statistically attribute synthetic media to specific generator families (Latent Diffusion, StyleGAN, Midjourney, ElevenLabs voice cloning, Sora/Veo video models).
            </p>
            <div className="p-3 rounded-xl bg-surface-2 border border-subtle text-[0.6875rem] text-ink-muted">
              <strong>Analytical Indicator:</strong> Model attribution is an investigative lead, decoupled from legal provenance verification.
            </div>
          </div>

          <div className="p-6 rounded-2xl border border-subtle bg-surface-1 space-y-3">
            <div className="flex items-center gap-2.5 text-accent">
              <Globe size={20} />
              <h3 className="text-base font-extrabold text-ink-primary">4. Physical World Consistency</h3>
            </div>
            <p className="text-xs text-ink-secondary leading-relaxed">
              Evaluates environmental physics: 3D shadow cast angles, multi-light source reflections in cornea pupils, vanishing point geometry, and atmospheric perspective consistency.
            </p>
            <div className="p-3 rounded-xl bg-surface-2 border border-subtle text-[0.6875rem] text-ink-muted">
              <strong>Physics Validation:</strong> AI models frequently hallucinate inconsistent shadows or pupil glints that break 3D Euclidean ray-tracing laws.
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 7: EVIDENCE-FIRST VERDICT PRESENTATION (PHASE 31.6) ───── */}
      <section id="false-positive-safe" className="p-8 rounded-3xl border border-accent/30 bg-accent/5 space-y-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/40 bg-accent/10 text-accent text-[0.6875rem] font-bold uppercase tracking-widest mb-2">
            Phase 31.6 Standard • False-Positive Safe Presentation
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-ink-primary tracking-tight">
            Evidence-First Decision Policy & Scientific Humility
          </h2>
          <p className="text-xs sm:text-sm text-ink-secondary max-w-3xl mt-1 leading-relaxed">
            Forensic software loses credibility when it falsely accuses real images of being AI-generated. Our platform enforces strict mathematical separation between detector scores and systemic conclusions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-5 rounded-2xl border border-subtle bg-surface-1 space-y-2">
            <span className="font-bold text-accent uppercase text-[0.6875rem] block">The Core Principle</span>
            <div className="font-mono text-xs text-ink-primary p-2.5 rounded bg-surface-2 border border-subtle">
              RAW MODEL SCORE ≠ FINAL FORENSIC VERDICT<br />
              ABSENT METADATA ≠ AI GENERATION<br />
              MESSAGING COMPRESSION ≠ MANIPULATION
            </div>
            <p className="text-ink-secondary leading-relaxed pt-1">
              A vision transformer probe score of 79.6% is an isolated technical measurement, not proof that an image is synthetic. The UI displays raw model scores in Section B while reserving Section A for corroborated assessments.
            </p>
          </div>

          <div className="p-5 rounded-2xl border border-subtle bg-surface-1 space-y-2">
            <span className="font-bold text-accent uppercase text-[0.6875rem] block">WhatsApp / Social Media Safe UX</span>
            <div className="font-mono text-xs text-ink-primary p-2.5 rounded bg-surface-2 border border-subtle">
              Input Quality: FAIR • PURGED_METADATA • Trailing Bytes
            </div>
            <p className="text-ink-secondary leading-relaxed pt-1">
              Mobile messaging apps (WhatsApp, Telegram) recompress DCT coefficients and strip EXIF tags. The engine recognizes this transformation profile as reliability context, preventing false positives on genuine user photographs.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-subtle bg-surface-1 text-xs text-ink-secondary leading-relaxed flex items-start gap-3">
          <Info size={16} className="text-accent shrink-0 mt-0.5" />
          <div>
            <strong className="text-ink-primary block mb-0.5">Non-Sensationalist Language Policy:</strong>
            We ban alarmist phrasing like <em>"THREAT DETECTED"</em>, <em>"DEFINITELY FAKE"</em>, or <em>"CRIMINAL MEDIA"</em>. We report measured evidence, signal corroboration counts, physical sensor demosaicing, and honest <strong>INCONCLUSIVE</strong> determinations when evidence lacks consensus.
          </div>
        </div>
      </section>

      {/* ── SECTION 8: CHAIN OF CUSTODY & COURT ADMISSIBILITY ─────────────── */}
      <section id="chain-of-custody" className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <span className="text-[0.6875rem] font-black uppercase tracking-widest text-[#00E5FF]">Legal Admissibility</span>
            <h2 className="text-2xl sm:text-3xl font-black text-ink-primary tracking-tight">Chain of Custody & Court-Ready Dossiers</h2>
          </div>
          <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-surface-2 border border-subtle text-ink-secondary">
            ISO/IEC 27037 • Daubert Standard
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-5 rounded-2xl border border-subtle bg-surface-1 space-y-2.5">
            <span className="font-mono font-black text-xl text-accent">01</span>
            <h3 className="text-sm font-extrabold text-ink-primary">Immutable Ledgering</h3>
            <p className="text-xs text-ink-secondary leading-relaxed">
              Every analyzed file is registered with irreversible SHA-256 and SHA-512 hashes upon arrival. Evidence is stored in write-once read-many (WORM) storage to prevent tampering.
            </p>
          </div>
          <div className="p-5 rounded-2xl border border-subtle bg-surface-1 space-y-2.5">
            <span className="font-mono font-black text-xl text-accent">02</span>
            <h3 className="text-sm font-extrabold text-ink-primary">Court-Ready PDF Dossier</h3>
            <p className="text-xs text-ink-secondary leading-relaxed">
              Automated compilation of legal forensic exhibits, including Grad-CAM neural attention overlays, ELA differential plates, sensor noise variance, and calibrated fusion math.
            </p>
          </div>
          <div className="p-5 rounded-2xl border border-subtle bg-surface-1 space-y-2.5">
            <span className="font-mono font-black text-xl text-accent">03</span>
            <h3 className="text-sm font-extrabold text-ink-primary">Cryptographic Verification</h3>
            <p className="text-xs text-ink-secondary leading-relaxed">
              Generated PDF reports embed a tamper-evident digital seal. Any modification to report text, verdict, or timestamps immediately invalidates the offline cryptographic checksum.
            </p>
          </div>
        </div>
      </section>

      {/* ── SECTION 9: LIVE DEPLOYMENT TELEMETRY ──────────────────────────── */}
      <section id="telemetry" className="rounded-3xl border border-subtle bg-surface-1 p-6 sm:p-8 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[0.6875rem] font-black uppercase tracking-widest text-accent">Real-Time Infrastructure</span>
            <h2 className="text-xl sm:text-2xl font-black text-ink-primary tracking-tight">Active Deployment Status</h2>
          </div>
          <span className="flex items-center gap-1.5 text-xs font-mono font-bold text-emerald-400 px-2.5 py-1 rounded bg-surface-2 border border-subtle">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            LIVE ONLINE
          </span>
        </div>

        {health ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            <div className="p-3.5 rounded-xl border border-subtle bg-surface-2">
              <span className="text-[0.65rem] uppercase font-bold text-ink-muted block">Platform Engine</span>
              <span className="font-mono font-bold text-ink-primary text-sm mt-1 block">v{health.version}</span>
            </div>
            <div className="p-3.5 rounded-xl border border-subtle bg-surface-2">
              <span className="text-[0.65rem] uppercase font-bold text-ink-muted block">Asynchronous Queue</span>
              <span className="font-mono font-bold text-ink-primary text-sm mt-1 block">
                {health.queue_enabled ? 'Celery / Redis Active' : 'Inline Accelerated Worker'}
              </span>
            </div>
            <div className="p-3.5 rounded-xl border border-subtle bg-surface-2">
              <span className="text-[0.65rem] uppercase font-bold text-ink-muted block">GPU Acceleration</span>
              <span className="font-mono font-bold text-emerald-400 text-sm mt-1 block">
                CUDA / TensorRT Pre-Warmed
              </span>
            </div>
            <div className="p-3.5 rounded-xl border border-subtle bg-surface-2">
              <span className="text-[0.65rem] uppercase font-bold text-ink-muted block">Primary Checkpoint</span>
              <span className="font-mono font-bold text-ink-primary text-sm mt-1 block truncate" title={health.models?.image}>
                {health.models?.image ? health.models.image.split(',')[0] : 'EfficientNet-B4'}
              </span>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-surface-2 text-xs text-ink-muted">
            Fetching real-time deployment status from /api/health...
          </div>
        )}
      </section>

      {/* ── SECTION 10: SCIENTIFIC RIGOR & LIMITATIONS ────────────────────── */}
      <section id="limitations" className="rounded-3xl border border-subtle bg-surface-2 p-6 sm:p-8 space-y-5">
        <div>
          <span className="text-[0.6875rem] font-black uppercase tracking-widest text-ink-muted">Academic Standards</span>
          <h2 className="text-xl sm:text-2xl font-black text-ink-primary tracking-tight">Scientific Rigor & Known Limitations</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs leading-relaxed text-ink-secondary">
          <div className="space-y-2">
            <strong className="text-ink-primary block">Training Corpus & Split Discipline</strong>
            <p>
              Trained and validated on academic benchmarks (FFHQ, 140k Real & Fake Faces, FaceForensics++, ASVspoof, In-the-Wild Diffusion). Data splits are strictly partitioned by identity and source recording — never by individual video frame — avoiding artificial accuracy inflation.
            </p>
          </div>
          <div className="space-y-2">
            <strong className="text-ink-primary block">Domain Shift & Generator Evolution</strong>
            <p>
              Zero-day generative architectures appear continuously. While physical camera CFA demosaicing and PRNU noise residuals remain invariant physical signatures, neural pattern probes require periodic benchmark recalibration against new diffusion checkpoints.
            </p>
          </div>
          <div className="space-y-2">
            <strong className="text-ink-primary block">Resolution & Extreme Downsampling</strong>
            <p>
              Media with resolution below 224 × 224 px or subject faces occupying less than 5% of the frame lack sufficient high-frequency spatial coefficients for reliable neural extraction. The engine flags these as LIMITED_ANALYZABILITY.
            </p>
          </div>
          <div className="space-y-2">
            <strong className="text-ink-primary block">Investigative Lead, Not Legal Opinion</strong>
            <p>
              This system provides an automated technical forensic evaluation. In judicial proceedings, findings should be reviewed and corroborated by a certified digital forensics expert witness in accordance with ISO/IEC 27037 standards.
            </p>
          </div>
        </div>

        <div className="pt-4 border-t border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <span className="text-xs text-ink-muted">
            Ready to test media against our multi-modal forensic pipeline?
          </span>
          <Link to="/analyse" className="btn-primary py-2 px-4 text-xs font-bold inline-flex items-center gap-1.5 self-start sm:self-auto">
            <Upload size={14} /> Launch Analysis Lab
          </Link>
        </div>
      </section>

    </div>
  )
}
