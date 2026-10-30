import { Link } from 'react-router-dom'
import { Card } from '../components/ui'
import { 
  Database, Clock, Trash, ShieldAlert, Lock, ArrowLeft, Upload, CheckCircle
} from '../components/ui/Icons'

export default function Privacy() {
  return (
    <div className="mx-auto max-w-4xl animate-in space-y-8 py-6 px-4">
      <div className="flex items-center gap-3">
        <Link to="/analyse" className="btn-secondary py-1.5 px-3 text-xs inline-flex items-center gap-1.5">
          <ArrowLeft size={14} /> Back to Analysis
        </Link>
      </div>

      <header className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border bg-surface-1 text-[0.6875rem] font-bold uppercase tracking-widest text-ink-muted"
             style={{ borderColor: 'var(--border-subtle)' }}>
          <Lock size={12} className="text-accent" />
          Data Governance & Integrity
        </div>
        <h1 className="wide font-black uppercase text-ink-primary" style={{ fontSize: 'clamp(2.25rem, 5vw, 4rem)', lineHeight: 0.92, letterSpacing: '-0.055em' }}>
          Privacy &amp; Data <span className="serif-i normal-case text-gradient">Retention</span> Policy
        </h1>
        <p className="text-sm sm:text-base text-ink-secondary leading-relaxed max-w-2xl">
          Complete disclosure on how media is processed, what artifacts are stored, our automated retention lifecycle, and your rights to immediate permanent deletion.
        </p>
      </header>

      {/* ── KEY PRINCIPLES GRID ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. What is Stored */}
        <Card title="1. What Is Stored" subtitle="Media, diagnostic artifacts, and cryptographic digests" className="h-full">
          <div className="space-y-3 text-xs leading-relaxed text-ink-secondary">
            <p>
              When you submit media for inspection, the platform ingests and stores only the data strictly necessary to execute the forensic detection pipelines:
            </p>
            <ul className="space-y-2 pl-1">
              <li className="flex items-start gap-2">
                <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                <span>
                  <strong className="text-ink-primary">Source Media File:</strong> The uploaded image, audio clip, or video container, stored temporarily in an isolated on-premises file storage volume.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                <span>
                  <strong className="text-ink-primary">Forensic Evidence Artifacts:</strong> Diagnostic output plates generated during pipeline execution, such as Grad-CAM neural attention heatmaps, error level analysis (ELA) differentials, and audio spectrograms.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                <span>
                  <strong className="text-ink-primary">Cryptographic Checksums:</strong> Irreversible SHA-256 digests of the submitted media and generated technical PDF report.
                </span>
              </li>
            </ul>
            <div className="p-3 rounded-xl bg-surface-2 border border-subtle text-[0.6875rem] text-ink-muted">
              <strong className="text-ink-primary">No Biometric Identifiers:</strong> We do not extract, enroll, or store facial recognition templates, voiceprints, or identity biometrics. All neural analysis is purely artifact-driven.
            </div>
          </div>
        </Card>

        {/* 2. Retention Window */}
        <Card title="2. The Retention Window" subtitle="Automated purging and data lifecycles" className="h-full">
          <div className="space-y-3 text-xs leading-relaxed text-ink-secondary">
            <p>
              We enforce strict retention boundaries to prevent indefinite data storage:
            </p>
            <div className="space-y-3">
              <div className="p-3.5 rounded-xl border border-subtle bg-surface-2 space-y-1">
                <div className="flex items-center gap-2 text-ink-primary font-bold">
                  <Clock size={15} className="text-accent" />
                  <span>Guest Uploads: 72-Hour Ephemeral Retention</span>
                </div>
                <p className="text-[0.6875rem] text-ink-muted">
                  Analyses initiated by unregistered guests are governed by a strict <strong>72-hour retention window</strong>. An automated Celery beat cleanup service runs every hour to permanently delete all guest uploads, evidence files, and reports.
                </p>
              </div>

              <div className="p-3.5 rounded-xl border border-subtle bg-surface-2 space-y-1">
                <div className="flex items-center gap-2 text-ink-primary font-bold">
                  <Database size={15} className="text-accent" />
                  <span>Registered Accounts: User-Controlled History</span>
                </div>
                <p className="text-[0.6875rem] text-ink-muted">
                  Scans created by signed-in users persist in your personal History dashboard until you explicitly choose to delete them.
                </p>
              </div>
            </div>
          </div>
        </Card>

        {/* 3. How to Delete */}
        <Card title="3. How to Delete Your Data" subtitle="Immediate, permanent eradication" className="h-full">
          <div className="space-y-3 text-xs leading-relaxed text-ink-secondary">
            <p>
              You maintain complete ownership and control over your submitted evidence:
            </p>
            <ul className="space-y-2 pl-1">
              <li className="flex items-start gap-2">
                <Trash size={14} className="text-rose-500 mt-0.5 shrink-0" />
                <span>
                  <strong className="text-ink-primary">One-Click Immediate Deletion:</strong> Registered users can navigate to the <Link to="/history" className="text-accent underline font-semibold">History</Link> tab and click &quot;Delete scan&quot; on any record.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Trash size={14} className="text-rose-500 mt-0.5 shrink-0" />
                <span>
                  <strong className="text-ink-primary">Irreversible Storage Wipe:</strong> Deleting a scan permanently removes the uploaded media file, all derived evidence plates (*.png, *.jpg), and the compiled PDF dossier from disk storage and drops the database record.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Trash size={14} className="text-rose-500 mt-0.5 shrink-0" />
                <span>
                  <strong className="text-ink-primary">Guest Expiration:</strong> Guest submissions require no manual action; all associated files are automatically wiped upon expiration.
                </span>
              </li>
            </ul>
          </div>
        </Card>

        {/* 4. Legal Standing Disclaimer */}
        <Card title="4. Legal Standing Disclaimer" subtitle="Investigative triage vs judicial evidence" className="h-full">
          <div className="space-y-3 text-xs leading-relaxed text-ink-secondary">
            <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-500 space-y-1">
              <div className="flex items-center gap-2 font-bold">
                <ShieldAlert size={16} />
                <span>Automated Assessment Only — Not Legal Evidence</span>
              </div>
              <p className="text-[0.6875rem] text-ink-secondary leading-relaxed">
                Findings produced by DeepSentinel are automated technical evaluations intended solely for investigative triage. They do <strong>not</strong> constitute certified forensic expert opinions, legal evidence, or court-admissible testimony.
              </p>
            </div>
            <p>
              Neural networks and heuristic signal detectors produce statistical likelihoods. High compression, non-linear social media recompression, or extreme downsampling can generate false positives or false negatives.
            </p>
            <p>
              In legal disputes or judicial proceedings, media must always be independently reviewed and corroborated by a qualified, court-certified digital forensics specialist.
            </p>
          </div>
        </Card>
      </div>

      {/* ── FOOTER ACTIONS ── */}
      <div className="pt-4 border-t border-subtle flex flex-wrap items-center justify-between gap-4">
        <span className="text-xs text-ink-muted">
          Have media to evaluate under these strict privacy standards?
        </span>
        <Link to="/analyse" className="btn-primary py-2 px-4 text-xs font-bold inline-flex items-center gap-1.5">
          <Upload size={14} /> Launch Analysis Lab
        </Link>
      </div>
    </div>
  )
}
