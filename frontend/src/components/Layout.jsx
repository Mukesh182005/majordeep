import { useEffect } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { motion, useReducedMotion, useScroll, useSpring } from 'framer-motion'
import { api, clearSession } from '../lib/api'
import { useAuth } from '../lib/useAuth'
import { useTheme } from '../lib/theme'
import Cursor from './fx/Cursor'
import Footer from './Footer'
import { Moon, Sun } from './ui/Icons'

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `mono whitespace-nowrap rounded-md border-2 px-3 py-1.5 text-[0.75rem] font-bold uppercase tracking-wide transition-all duration-150 ${
          isActive
            ? 'border-[#191919] bg-sentinel-acid text-[#191919] shadow-[3px_3px_0_var(--pop)]'
            : 'border-transparent text-ink-secondary hover:border-edge-strong hover:text-ink-primary'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

function ThemeToggle() {
  const { resolved, setTheme } = useTheme()
  const next = resolved === 'dark' ? 'light' : 'dark'
  return (
    <button
      onClick={() => setTheme(next)}
      className="grid h-9 w-9 place-items-center rounded-md border-2 border-edge-strong text-ink-secondary transition-all hover:rotate-12 hover:border-[var(--line)] hover:text-ink-primary"
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      {resolved === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}

/** Sentinel mark: an eye inside a shield, on an acid tile. */
export function LogoMark({ size = 38 }) {
  return (
    <span
      className="grid shrink-0 place-items-center rounded-md border-2 border-[#191919] transition-transform duration-300 group-hover:-rotate-6"
      style={{ width: size, height: size, background: 'var(--acid)', boxShadow: '3px 3px 0 var(--pop)' }}
    >
      <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 24 24" fill="none" stroke="#191919"
           strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 2.5 20 6v6c0 5-3.4 8.4-8 9.5C7.4 20.4 4 17 4 12V6z" />
        <path d="M7.5 12.2c1.2-2 2.7-3 4.5-3s3.3 1 4.5 3c-1.2 2-2.7 3-4.5 3s-3.3-1-4.5-3z" />
        <circle cx="12" cy="12.2" r="1.3" fill="#191919" />
      </svg>
    </span>
  )
}

export default function Layout() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const reduceMotion = useReducedMotion()
  const { scrollYProgress } = useScroll()
  const progress = useSpring(scrollYProgress, { stiffness: 140, damping: 30, restDelta: 0.001 })

  // New page: jump to the #section the link named, or to the top.
  useEffect(() => {
    if (location.hash) {
      const t = window.setTimeout(() => document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'smooth' }), 350)
      return () => window.clearTimeout(t)
    }
    window.scrollTo(0, 0)
    return undefined
  }, [location.pathname, location.hash])

  async function signOut() {
    // The session is an httpOnly cookie only the server can clear; without this call the
    // next page load signed the user straight back in.
    try {
      await api.logout()
    } catch {
      /* already signed out or offline: clear the local state anyway */
    }
    clearSession()
    setUser(null)
    navigate('/')
  }

  const links = (
    <>
      <NavItem to="/analyse">Analyse</NavItem>
      {user && <NavItem to="/history">History</NavItem>}
      <NavItem to="/how-it-works">How it works</NavItem>
    </>
  )

  return (
    <div className="flex min-h-screen flex-col">
      <div className="grain" aria-hidden="true" />
      <Cursor />

      {/* ── Header ──────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 border-b-2"
              style={{ backgroundColor: 'var(--surface-page)', borderColor: 'var(--border-strong)' }}>
        <div className="mx-auto flex h-16 max-w-content items-center justify-between gap-3 px-4 sm:px-6 lg:px-10">
          <Link to="/" className="group flex items-center gap-3" aria-label="DeepSentinel home">
            <LogoMark />
            <span className="leading-none">
              <span className="wide block text-[1.1875rem] font-black tracking-tight text-ink-primary">
                Deep<span className="text-gradient">Sentinel</span>
              </span>
              <span className="mono mt-1 hidden text-[0.625rem] uppercase tracking-[0.14em] text-ink-muted sm:block">
                deepfake detection
              </span>
            </span>
          </Link>

          <nav className="flex items-center gap-2">
            <div className="mr-1 hidden items-center gap-1.5 sm:flex">{links}</div>

            <ThemeToggle />

            {user ? (
              <div className="flex items-center gap-2.5">
                <span className="hidden max-w-[11rem] truncate text-[0.8125rem] text-ink-muted md:block">
                  {user.email}
                </span>
                <button onClick={signOut} className="btn-secondary !py-1.5 text-[0.8125rem]">
                  Sign out
                </button>
              </div>
            ) : (
              <Link to="/login" className="btn-primary !py-1.5 text-[0.8125rem]">
                Sign in
              </Link>
            )}
          </nav>
        </div>

        {/* Reading progress */}
        <motion.div className="scroll-progress absolute inset-x-0 -bottom-[2px] h-[3px]"
                    style={{ scaleX: progress, background: 'var(--acid)' }}
                    aria-hidden="true" />

        {/* Mobile nav: the row above is hidden under 640px. */}
        <div className="flex items-center gap-1.5 overflow-x-auto border-t-2 px-4 py-2 sm:hidden"
             style={{ borderColor: 'var(--border-subtle)' }}>
          {links}
        </div>
      </header>

      {/* ── Main content ────────────────────────────────────────────── */}
      <main className="mx-auto w-full max-w-content flex-1 px-4 py-10 sm:px-6 lg:px-10">
        {/* Keyed by path so each page slides in on navigation. */}
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.2, 0.9, 0.3, 1] }}
        >
          <Outlet />
        </motion.div>
        {/* curtain: an acid panel that sweeps off the screen on each page change */}
        {!reduceMotion && <motion.div
          key={`curtain-${location.pathname}`}
          className="pointer-events-none fixed inset-0 z-[80] origin-top"
          style={{ background: 'var(--acid)' }}
          initial={{ scaleY: 1 }}
          animate={{ scaleY: 0 }}
          transition={{ duration: 0.55, ease: [0.7, 0, 0.2, 1] }}
          aria-hidden="true"
        />}
      </main>

      <Footer />
    </div>
  )
}
