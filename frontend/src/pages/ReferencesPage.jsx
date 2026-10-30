import References from '../components/howitworks/References'

/** Standalone references page, linked from the footer only. */
export default function ReferencesPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <span className="eyebrow">References</span>
      <h1 className="wide mt-4 font-black uppercase text-ink-primary"
          style={{ fontSize: 'clamp(2.5rem, 6vw, 5.25rem)', lineHeight: 0.88, letterSpacing: '-0.055em' }}>
        Standing on <span className="serif-i normal-case text-gradient">these.</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[1.0625rem] leading-relaxed text-ink-secondary">
        Every model, dataset, document and tool DeepSentinel is built on. Linked entries open the original
        source; the rest live in the project repository.
      </p>
      <div className="mt-10">
        <References />
      </div>
    </div>
  )
}
