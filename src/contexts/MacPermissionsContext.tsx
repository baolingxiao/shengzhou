import { createContext, useContext, useState, type ReactNode } from 'react'
import { useMacPermissions, type MacPermissionsState } from '../hooks/useMacPermissions'

type MacPermissionsContextValue = MacPermissionsState & {
  statusPanelOpen: boolean
  openStatusPanel: () => void
  closeStatusPanel: () => void
}

const MacPermissionsContext = createContext<MacPermissionsContextValue | null>(null)

export function MacPermissionsProvider({ children }: { children: ReactNode }) {
  const perms = useMacPermissions(true)
  const [statusPanelOpen, setStatusPanelOpen] = useState(false)

  return (
    <MacPermissionsContext.Provider
      value={{
        ...perms,
        statusPanelOpen,
        openStatusPanel: () => setStatusPanelOpen(true),
        closeStatusPanel: () => setStatusPanelOpen(false),
      }}
    >
      {children}
    </MacPermissionsContext.Provider>
  )
}

export function useMacPermissionsContext(): MacPermissionsContextValue {
  const ctx = useContext(MacPermissionsContext)
  if (!ctx) {
    throw new Error('useMacPermissionsContext must be used within MacPermissionsProvider')
  }
  return ctx
}
