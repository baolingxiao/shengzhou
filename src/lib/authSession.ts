const AUTH_KEY = 'jarvis-auth'

export type AuthSession = {
  username: string
  loggedInAt: number
  isAdmin: boolean
}

export function readAuthSession(): AuthSession | null {
  try {
    const raw = sessionStorage.getItem(AUTH_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<AuthSession>
    if (typeof parsed.username !== 'string' || !parsed.username.trim()) return null
    return {
      username: parsed.username.trim(),
      loggedInAt: typeof parsed.loggedInAt === 'number' ? parsed.loggedInAt : Date.now(),
      isAdmin: parsed.isAdmin === true,
    }
  } catch {
    return null
  }
}

export function writeAuthSession(session: AuthSession): void {
  sessionStorage.setItem(AUTH_KEY, JSON.stringify(session))
}

export function clearAuthSession(): void {
  sessionStorage.removeItem(AUTH_KEY)
}
