import { AlertTriangle, Info } from './ui/Icons'

/**
 * "How this verdict was reached": the verdict basis the pipeline reports
 * (evidence.verdict_basis), each AI detector's own score
 * (evidence.scene_model_scores) and the pipeline's notes (evidence.notes),
 * which include the "AI detectors disagree" warning from image_pipeline.py.
 */

const BASIS = {
  detector_score: 'Decided by the combined score of the AI-generation detectors.',
  learned_combination: 'Decided by the learned combination of the AI-generation detectors, fitted on held-out images.',
  scene_detectors_unavailable: 'The AI-generation detectors could not run, so the result cannot be called authentic.',
  screen_recapture: 'This looks like a screenshot or screen photo: camera provenance is lost, so a low score cannot confirm the image is genuine.',
  weak_indicators_no_camera_metadata: 'The score is low but there is no camera metadata, so the image is not called authentic.',
}

// Same rule the pipeline uses for its disagreement note.
const disagree = (ps) => ps.length > 1 && Math.max(...ps) >= 0.9 && Math.min(...ps) <= 0.1

export default function VerdictBasis({ evidence = {} }) {
  const basis = evidence.verdict_basis
  const scores = Object.entries(evidence.scene_model_scores || {}).filter(([, p]) => typeof p === 'number')
  const notes = (evidence.notes || []).filter(Boolean)
  if (!basis && !scores.length && !notes.length) return null
  const split = disagree(scores.map(([, p]) => p))

  return (
    <section className="card mb-6 p-6" aria-label="How this verdict was reached" data-testid="verdict-basis">
      <h2 className="text-lg font-black tracking-tight text-ink-primary">How this verdict was reached</h2>
      {basis && (
        <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink-secondary">
          {BASIS[basis] || `Basis: ${basis.replace(/_/g, ' ')}.`}
        </p>
      )}

      {scores.length > 0 && (
        <div className="mt-5">
          <p className="mono text-[0.6875rem] font-bold uppercase tracking-wider text-ink-muted">Each detector&apos;s own score (probability of AI generation)</p>
          <ul className="mt-3 space-y-3">
            {scores.map(([name, p]) => (
              <li key={name}>
                <div className="flex items-baseline justify-between gap-3 text-[0.875rem]">
                  <span className="font-semibold text-ink-primary">{name}</span>
                  <span className="mono tnum font-bold text-ink-primary">{(p * 100).toFixed(1)}%</span>
                </div>
                <div className="mt-1 h-2.5 overflow-hidden rounded-full" style={{ background: 'var(--surface-3)' }}>
                  <div className="h-full rounded-full"
                       style={{ width: `${Math.max(1, p * 100)}%`, background: p >= 0.58 ? 'var(--status-critical)' : p > 0.42 ? 'var(--status-warn)' : 'var(--status-good)' }} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {split && (
        <div className="mt-5 flex gap-3 rounded-lg border p-4" role="note"
             style={{ borderColor: 'var(--status-warn)', background: 'var(--status-warn-bg)' }}>
          <AlertTriangle size={18} className="mt-0.5 shrink-0" style={{ color: 'var(--status-warn)' }} />
          <p className="text-[0.875rem] leading-relaxed text-ink-primary">
            <strong>The detectors disagree.</strong> At least one is very confident the image is AI-generated and at least one is
            very confident it is not. Treat this verdict with extra caution.
          </p>
        </div>
      )}

      {notes.length > 0 && (
        <ul className="mt-5 space-y-2">
          {notes.map((n) => (
            <li key={n} className="flex gap-2.5 text-[0.875rem] leading-relaxed text-ink-secondary">
              <Info size={15} className="mt-0.5 shrink-0 text-accent" />
              <span>{n}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
