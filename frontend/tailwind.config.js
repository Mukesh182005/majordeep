// Sentinel palette (charcoal + greens). The forensic views use Tailwind's stock
// colour names (emerald, rose, indigo, sky...) in a few hundred places;
// remapping the scales here restyles all of them at once. Red and amber stay
// as warning colours: a "likely fake" verdict must never read as green.
const acid = {
  50: '#e8fff0', 100: '#c4fdd8', 200: '#6dfbb4', 300: '#47f987', 400: '#23f871',
  500: '#07f25b', 600: '#05c94b', 700: '#04a03c', 800: '#036727', 900: '#024219', 950: '#012a10',
}
const mint = {
  50: '#e3f5ec', 100: '#a7e1c5', 200: '#8cd8b3', 300: '#72cfa1', 400: '#57c690',
  500: '#3fb87e', 600: '#2e9f6a', 700: '#246a48', 800: '#1b4f36', 900: '#123524', 950: '#0b2117',
}
const teal = {
  50: '#e6f5f2', 100: '#a9ddd5', 200: '#8fd1c6', 300: '#75ccbe', 400: '#5ac2af',
  500: '#43b6a1', 600: '#399a8a', 700: '#2f8273', 800: '#26685c', 900: '#19443c', 950: '#13342e',
}
const signal = {
  50: '#fff1ef', 100: '#ffdcd7', 200: '#ffb9b0', 300: '#ff8f82', 400: '#ff6a5a',
  500: '#ff4d3d', 600: '#e5321f', 700: '#bf2617', 800: '#9b2216', 900: '#7f2016', 950: '#450b05',
}
const amber = {
  50: '#fff9eb', 100: '#ffefc6', 200: '#ffdd88', 300: '#ffcb4f', 400: '#ffbe33',
  500: '#ffb020', 600: '#e08e00', 700: '#b86e00', 800: '#94560a', 900: '#7a470d', 950: '#462402',
}
const charcoal = {
  50: '#ececed', 100: '#c2c2c5', 200: '#a7a7ab', 300: '#9d9da4', 400: '#8a8a92',
  500: '#787881', 600: '#67676e', 700: '#56565c', 800: '#444449', 900: '#28282b', 950: '#191919',
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        emerald: acid,
        green: acid,
        lime: acid,
        rose: signal,
        red: signal,
        orange: signal,
        indigo: teal,
        purple: teal,
        violet: teal,
        pink: mint,
        fuchsia: mint,
        sky: mint,
        cyan: mint,
        blue: mint,
        teal,
        amber,
        yellow: amber,
        slate: charcoal,
        gray: charcoal,
        zinc: charcoal,
        acid,
        mint,
        charcoal,
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
        neon: {
          cyan: 'var(--neon-cyan)',
          violet: 'var(--neon-violet)',
          magenta: 'var(--neon-magenta)',
          lime: 'var(--neon-lime)',
        },
        sentinel: {
          acid: 'var(--acid)',
          mint: 'var(--mint)',
          teal: 'var(--teal)',
          forest: 'var(--forest)',
          pine: 'var(--pine)',
          sea: 'var(--sea)',
          ink: 'var(--ink)',
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
        sans: ['Archivo', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['Archivo', 'system-ui', 'sans-serif'],
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
        mono: ['"Space Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
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
