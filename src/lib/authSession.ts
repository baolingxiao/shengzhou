const AUTH_KEY = 'jarvis-auth'

export type AuthSession = {
  username: string
  loggedInAt: number
  role: 'developer' | 'user'
  isAdmin: boolean
  accessToken: string
}

export function readAuthSession(): AuthSession | null {
  try {
    const raw = sessionStorage.getItem(AUTH_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<AuthSession>
    if (typeof parsed.username !== 'string' || !parsed.username.trim()) return null
    const accessToken = typeof parsed.accessToken === 'string' ? parsed.accessToken : ''
    if (!accessToken.trim()) return null
    return {
      username: parsed.username.trim(),
      loggedInAt: typeof parsed.loggedInAt === 'number' ? parsed.loggedInAt : Date.now(),
      role: parsed.role === 'user' ? 'user' : 'developer',
      isAdmin: parsed.isAdmin === true,
      accessToken,
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

export function authHeaders(base?: HeadersInit): HeadersInit {
  const session = readAuthSession()
  const headers = new Headers(base ?? undefined)
  if (session?.accessToken) {
    headers.set('Authorization', `Bearer ${session.accessToken}`)
  }
  return headers
}
