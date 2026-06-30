import { useCallback, useState } from 'react'
import { login as loginRequest } from '../lib/authApi'
import {
  clearAuthSession,
  readAuthSession,
  writeAuthSession,
  type AuthSession,
} from '../lib/authSession'

export function useAuth() {
  const [session, setSession] = useState<AuthSession | null>(() => readAuthSession())
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loggingIn, setLoggingIn] = useState(false)

  const login = useCallback(async (username: string, password: string) => {
    setLoginError(null)
    setLoggingIn(true)
    try {
      const result = await loginRequest(username.trim(), password)
      const next: AuthSession = {
        username: result.username,
        loggedInAt: Date.now(),
        isAdmin: Boolean(result.is_admin),
      }
      writeAuthSession(next)
      setSession(next)
    } catch (err) {
      const message = err instanceof Error ? err.message : '登录失败'
      setLoginError(message)
      throw err
    } finally {
      setLoggingIn(false)
    }
  }, [])

  const logout = useCallback(() => {
    clearAuthSession()
    setSession(null)
    setLoginError(null)
    window.location.reload()
  }, [])

  return {
    session,
    isAuthenticated: session !== null,
    username: session?.username ?? null,
    isAdmin: session?.isAdmin ?? false,
    login,
    logout,
    loginError,
    loggingIn,
  }
}
