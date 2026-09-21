/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        surface: {
          page: 'var(--surface-page)',
          1: 'var(--surface-1)',
          2: 'var(--surface-2)',
          3: 'var(--surface-3)',
        },
        edge: {
          subtle: 'var(--border-subtle)',
          strong: 'var(--border-strong)',
        },
        ink: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          inverse: 'var(--text-inverse)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          soft: 'var(--accent-soft)',
        },
        status: {
          good: 'var(--status-good)',
          'good-bg': 'var(--status-good-bg)',
          warn: 'var(--status-warn)',
          'warn-bg': 'var(--status-warn-bg)',
          critical: 'var(--status-critical)',
          'crit-bg': 'var(--status-crit-bg)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      letterSpacing: { tightest: '-0.04em', tight: '-0.025em' },
      fontSize: {
        'display-xl': ['clamp(2.5rem, 5vw + 0.5rem, 5rem)', { lineHeight: '1.08', letterSpacing: '-0.04em', fontWeight: '800' }],
        'display-lg': ['clamp(2rem, 3.5vw + 0.5rem, 3.75rem)', { lineHeight: '1.1', letterSpacing: '-0.035em', fontWeight: '800' }],
        'display-md': ['clamp(1.5rem, 2vw + 0.5rem, 2.5rem)', { lineHeight: '1.15', letterSpacing: '-0.03em', fontWeight: '700' }],
        'display-sm': ['clamp(1.25rem, 1.5vw + 0.25rem, 1.875rem)', { lineHeight: '1.2', letterSpacing: '-0.025em', fontWeight: '700' }],
      },
      boxShadow: {
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },
      maxWidth: {
        content: '100rem',       // 1600px — big monitor optimized
        'content-wide': '120rem', // 1920px — fullscreen hero sections
      },
      screens: {
        '2xl': '1536px',
        '3xl': '1920px',
      },
      backgroundImage: {
        'grad-accent':  'var(--grad-accent)',
        'grad-emerald': 'var(--grad-emerald)',
        'grad-hero':    'var(--grad-hero)',
      },
    },
  },
  plugins: [],
}
