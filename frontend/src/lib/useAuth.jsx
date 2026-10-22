import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api, getStoredUser, getToken, clearSession } from './api'

const AuthContext = createContext({ user: null, setUser: () => {}, loading: true })

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .me()
      .then((currentUser) => {
        setUser(currentUser)
      })
      .catch(() => {
        clearSession()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo(() => ({ user, setUser, loading }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
