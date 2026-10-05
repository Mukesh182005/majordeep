import { ShieldAlert, ShieldCheck, ShieldQuestion } from '../components/ui/Icons'

/**
 * Verdict presentation.
 *
 * Every verdict carries an icon and a label alongside its colour — status is
 * never signalled by colour alone.
 */
export const VERDICT = {
  likely_authentic: {
    label: 'Likely authentic',
    short: 'Likely Authentic',
    tone: 'good',
    color: 'var(--status-good)',
    bg: 'var(--status-good-bg)',
    icon: ShieldCheck,
    blurb: 'No strong indicators of manipulation or synthetic generation were found in this file.',
  },
  authentic: {
    label: 'Likely authentic',
    short: 'Likely Authentic',
    tone: 'good',
    color: 'var(--status-good)',
    bg: 'var(--status-good-bg)',
    icon: ShieldCheck,
    blurb: 'No strong indicators of manipulation or synthetic generation were found in this file.',
  },
  AUTHENTIC: {
    label: 'Likely authentic',
    short: 'Likely Authentic',
    tone: 'good',
    color: 'var(--status-good)',
    bg: 'var(--status-good-bg)',
    icon: ShieldCheck,
    blurb: 'No strong indicators of manipulation or synthetic generation were found in this file.',
  },
  likely_manipulated: {
    label: 'Likely manipulated',
    short: 'Likely Manipulated',
    tone: 'warn',
    color: 'var(--status-warn)',
    bg: 'var(--status-warn-bg)',
    icon: ShieldAlert,
    blurb: 'Signals consistent with AI generation or manipulation were detected.',
  },
  manipulated: {
    label: 'Likely manipulated',
    short: 'Likely Manipulated',
    tone: 'warn',
    color: 'var(--status-warn)',
    bg: 'var(--status-warn-bg)',
    icon: ShieldAlert,
    blurb: 'Signals consistent with AI generation or manipulation were detected.',
  },
  MANIPULATED: {
    label: 'Likely manipulated',
    short: 'Likely Manipulated',
    tone: 'warn',
    color: 'var(--status-warn)',
    bg: 'var(--status-warn-bg)',
    icon: ShieldAlert,
    blurb: 'Signals consistent with AI generation or manipulation were detected.',
  },
  likely_ai_generated: {
    label: 'Likely AI-generated',
    short: 'Likely AI-Gen',
    tone: 'warn',
    color: 'var(--amber)',
    bg: 'var(--amber-soft)',
    icon: ShieldAlert,
    blurb: 'Signals consistent with synthetic generative model synthesis were detected.',
  },
  inconclusive: {
    label: 'Inconclusive',
    short: 'Inconclusive',
    tone: 'neutral',
    color: '#94a3b8',
    bg: 'rgba(148, 163, 184, 0.1)',
    icon: ShieldQuestion,
    blurb: 'Available evidence does not support a sufficiently reliable AI-generation or manipulation determination.',
  },
  INCONCLUSIVE: {
    label: 'Inconclusive',
    short: 'Inconclusive',
    tone: 'neutral',
    color: '#94a3b8',
    bg: 'rgba(148, 163, 184, 0.1)',
    icon: ShieldQuestion,
    blurb: 'Available evidence does not support a sufficiently reliable AI-generation or manipulation determination.',
  },
  no_determination: {
    label: 'No determination',
    short: 'No Determination',
    tone: 'neutral',
    color: 'var(--text-muted)',
    bg: 'var(--surface-2)',
    icon: ShieldQuestion,
    blurb: 'Available forensic signals do not permit a conclusive determination.',
  },
}

export function verdictMeta(verdict) {
  if (!verdict) {
    return {
      label: 'Not analysed',
      short: 'Pending',
      tone: 'neutral',
      color: 'var(--text-muted)',
      bg: 'var(--surface-2)',
      icon: ShieldQuestion,
      blurb: '',
    }
  }

  if (VERDICT[verdict]) {
    return VERDICT[verdict]
  }

  const key = String(verdict).toLowerCase().trim()
  if (key === 'authentic' || key === 'likely_authentic') {
    return VERDICT.AUTHENTIC
  }
  if (key === 'manipulated' || key === 'likely_manipulated') {
    return VERDICT.MANIPULATED
  }
  if (key === 'inconclusive') {
    return VERDICT.INCONCLUSIVE
  }

  return (
    VERDICT[key] || {
      label: 'Not analysed',
      short: 'Pending',
      tone: 'neutral',
      color: 'var(--text-muted)',
      bg: 'var(--surface-2)',
      icon: ShieldQuestion,
      blurb: '',
    }
  )
}

export function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatDuration(ms) {
  if (!ms && ms !== 0) return '—'
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
}

export function percent(value, digits = 1) {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(digits)}%`
}
