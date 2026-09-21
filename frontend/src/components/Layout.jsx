import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { clearSession } from '../lib/api'
import { useAuth } from '../lib/useAuth'
import { useTheme } from '../lib/theme'
import { Moon, ShieldCheck, Sun } from './ui/Icons'

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `relative rounded-lg px-3.5 py-1.5 font-medium transition-all duration-150 text-sm ${
          isActive
            ? 'text-ink-primary bg-surface-2'
            : 'text-ink-muted hover:text-ink-primary hover:bg-surface-2'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {children}
          {isActive && (
            <span
              className="absolute inset-x-3 -bottom-[17px] h-[2px] rounded-full"
              style={{ background: 'var(--grad-accent)' }}
            />
          )}
        </>
      )}
    </NavLink>
  )
}

function ThemeToggle() {
  const { resolved, setTheme } = useTheme()
  const next = resolved === 'dark' ? 'light' : 'dark'
  return (
    <button
      onClick={() => setTheme(next)}
      className="btn-ghost h-9 w-9 !px-0 rounded-lg"
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      {resolved === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}

export default function Layout() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()

  function signOut() {
    clearSession()
    setUser(null)
    navigate('/')
  }

  return (
    <div className="flex min-h-screen flex-col">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-30 border-b backdrop-blur-xl blueprint-bg"
        style={{
          backgroundColor: 'color-mix(in srgb, var(--surface-1) 85%, transparent)',
          borderColor: 'var(--border-subtle)',
          boxShadow: '0 1px 0 var(--border-subtle)',
        }}
      >
        <div className="mx-auto flex h-16 max-w-content items-center justify-between px-6 lg:px-10">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <span
              className="grid h-9 w-9 place-items-center rounded-xl text-white transition-all duration-200 group-hover:scale-105"
              style={{ background: 'var(--grad-accent)', boxShadow: '0 2px 12px rgba(42,120,214,0.35)' }}
            >
              <ShieldCheck size={18} />
            </span>
            <span className="leading-none">
              <span
                className="block font-extrabold tracking-tight"
                style={{ fontSize: 'clamp(1rem, 1.2vw, 1.1875rem)', letterSpacing: '-0.03em' }}
              >
                Veritas
              </span>
              <span className="mt-0.5 block text-[0.7rem] font-medium tracking-wide uppercase text-ink-muted">
                Deepfake Forensics
              </span>
            </span>
          </Link>

          {/* Nav */}
          <nav className="flex items-center gap-1">
            <div className="mr-3 hidden items-center gap-0.5 sm:flex">
              <NavItem to="/analyse">Analyse</NavItem>
              {user && <NavItem to="/history">History</NavItem>}
              <NavItem to="/how-it-works">How it works</NavItem>
            </div>

            <ThemeToggle />

            {user ? (
              <div className="ml-2 flex items-center gap-2.5">
                <span className="hidden max-w-[11rem] truncate text-[0.8125rem] text-ink-muted md:block">
                  {user.email}
                </span>
                <button onClick={signOut} className="btn-secondary !py-1.5 text-[0.8125rem]">
                  Sign out
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="btn-primary ml-2 !py-1.5 text-[0.8125rem]"
              >
                Sign in
              </Link>
            )}
          </nav>
        </div>
      </header>

      {/* ── Main content ────────────────────────────────────────────── */}
      <main className="mx-auto w-full max-w-content flex-1 px-6 py-10 lg:px-10">
        <Outlet />
      </main>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t mt-8" style={{ borderColor: 'var(--border-subtle)' }}>
        <div className="mx-auto max-w-content px-6 py-10 lg:px-10">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">

            {/* Brand + disclaimer */}
            <div className="max-w-xl">
              <div className="flex items-center gap-2.5 mb-3">
                <span
                  className="grid h-7 w-7 place-items-center rounded-lg text-white"
                  style={{ background: 'var(--grad-accent)' }}
                >
                  <ShieldCheck size={14} />
                </span>
                <span className="font-bold text-ink-primary tracking-tight">Veritas</span>
                <span className="badge badge-neutral">Deepfake Forensics Platform</span>
              </div>
              <p className="text-[0.8125rem] font-semibold text-ink-primary">
                Automated technical assessment — not a certified forensic opinion.
              </p>
              <p className="mt-2 text-[0.75rem] leading-relaxed text-ink-muted">
                This platform produces an evidence report you may attach to a complaint. Detection
                models produce both false positives and false negatives. For legal proceedings,
                verification by a certified forensic expert is recommended.
              </p>
            </div>

            {/* Right column */}
            <div className="text-[0.75rem] leading-relaxed text-ink-muted sm:text-right shrink-0">
              <p className="font-semibold text-ink-secondary mb-2">Acceptable use</p>
              <p className="max-w-xs sm:ml-auto">
                Analyse only media you own or are authorised to analyse.
                Generating deepfakes with this tool is prohibited.
              </p>
              <p className="mt-4 text-ink-muted opacity-60">
                © {new Date().getFullYear()} Veritas Forensics Platform
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
