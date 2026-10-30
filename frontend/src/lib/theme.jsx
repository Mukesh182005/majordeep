import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const KEY = 'dfd.theme'
const ThemeContext = createContext({ theme: 'dark', setTheme: () => {}, resolved: 'dark' })

function readStored() {
  try {
    return localStorage.getItem(KEY) || 'dark'
  } catch {
    return 'dark'
  }
}

/**
 * Theme provider.
 *
 * Dark is the default. An explicit light or dark choice wins over the OS
 * setting; "system" follows `prefers-color-scheme`. The resolved value is
 * always stamped on `data-theme`, so the CSS tokens and Tailwind's `dark:`
 * variant agree.
 */
export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(readStored)
  const [resolved, setResolved] = useState('dark')

  useEffect(() => {
    const root = document.documentElement
    const media = window.matchMedia('(prefers-color-scheme: dark)')

    function apply() {
      const next = theme === 'system' ? (media.matches ? 'dark' : 'light') : theme
      root.setAttribute('data-theme', next)
      setResolved(next)
    }

    apply()
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [theme])

  const setTheme = useCallback((next) => {
    setThemeState(next)
    try {
      localStorage.setItem(KEY, next)
    } catch {
      /* storage blocked — the choice still applies for this session */
    }
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolved }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => useContext(ThemeContext)
