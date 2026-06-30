import { createContext, useContext, type ReactNode } from 'react'
import type { AuthSession } from '../lib/authSession'
import { resolveSessionId, resolveUserId } from '../lib/userSession'

export type UserSessionValue = {
  username: string | null
  userId: string | null
  sessionId: string
  loggedInAt: number | null
  role: 'developer' | 'user' | null
  isAdmin: boolean
}

const UserSessionContext = createContext<UserSessionValue>({
  username: null,
  userId: null,
  sessionId: 'default',
  loggedInAt: null,
  role: null,
  isAdmin: false,
})

type UserSessionProviderProps = {
  session: AuthSession | null
  children: ReactNode
}

export function UserSessionProvider({ session, children }: UserSessionProviderProps) {
  const username = session?.username ?? null
  const userId = username ? resolveUserId(username) : null
  const sessionId = resolveSessionId(username)

  return (
    <UserSessionContext.Provider
      value={{
        username,
        userId,
        sessionId,
        loggedInAt: session?.loggedInAt ?? null,
        role: session?.role ?? null,
        isAdmin: session?.isAdmin ?? false,
      }}
    >
      {children}
    </UserSessionContext.Provider>
  )
}

export function useUserSession(): UserSessionValue {
  return useContext(UserSessionContext)
}
