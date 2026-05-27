import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'

export function useAuth() {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)

  // On mount, verify token
  useEffect(() => {
    if (!api.isLoggedIn()) { setLoading(false); return }
    api.me()
      .then(d => setUser(d.user))
      .catch(() => { api.setToken(null); setUser(null) })
      .finally(() => setLoading(false))
  }, [])

  const register = useCallback(async (name, email, password) => {
    const d = await api.register(name, email, password)
    setUser(d.user)
    return d
  }, [])

  const login = useCallback(async (email, password) => {
    const d = await api.login(email, password)
    setUser(d.user)
    return d
  }, [])

  const logout = useCallback(async () => {
    await api.logout().catch(() => {})
    setUser(null)
  }, [])

  return { user, loading, register, login, logout }
}
