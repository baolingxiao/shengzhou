import { useCallback, useEffect, useRef, useState } from 'react'
import {
  applyAppUpdate,
  checkAppUpdate,
  dismissAppUpdate,
  type UpdateCheckResult,
} from '../lib/systemApi'
import { getSettingsIntervalMs } from '../lib/pwaChannel'

const DISMISS_KEY = 'jarvis_update_dismissed_sw'

export type BackendUpdateState = {
  info: UpdateCheckResult | null
  backendUpdateReady: boolean
  checking: boolean
  applying: boolean
  refreshCheck: (force?: boolean) => Promise<void>
  applyBackendUpdate: () => Promise<{ ok: boolean; message: string }>
  dismissBackendUpdate: () => Promise<void>
}

export function useBackendUpdate(enabled: boolean): BackendUpdateState {
  const [info, setInfo] = useState<UpdateCheckResult | null>(null)
  const [checking, setChecking] = useState(false)
  const [applying, setApplying] = useState(false)
  const dismissedRef = useRef<string | null>(
    typeof localStorage !== 'undefined' ? localStorage.getItem(DISMISS_KEY) : null,
  )

  const refreshCheck = useCallback(
    async (force = false) => {
      if (!enabled) return
      setChecking(true)
      try {
        const result = await checkAppUpdate(force)
        setInfo(result)
      } catch {
        setInfo(null)
      } finally {
        setChecking(false)
      }
    },
    [enabled],
  )

  useEffect(() => {
    if (!enabled) return
    void refreshCheck()
    const id = window.setInterval(() => void refreshCheck(), getSettingsIntervalMs())
    return () => window.clearInterval(id)
  }, [enabled, refreshCheck])

  const backendUpdateReady = Boolean(
    info?.update_available &&
      info.build_id &&
      dismissedRef.current !== info.build_id,
  )

  const applyBackendUpdate = useCallback(async () => {
    setApplying(true)
    try {
      const result = await applyAppUpdate()
      if (result.ok) {
        window.setTimeout(() => window.location.reload(), 1500)
      }
      return result
    } finally {
      setApplying(false)
    }
  }, [])

  const dismissBackendUpdate = useCallback(async () => {
    if (!info?.build_id) return
    dismissedRef.current = info.build_id
    localStorage.setItem(DISMISS_KEY, info.build_id)
    await dismissAppUpdate(info.build_id)
    await refreshCheck()
  }, [info?.build_id, refreshCheck])

  return {
    info,
    backendUpdateReady,
    checking,
    applying,
    refreshCheck,
    applyBackendUpdate,
    dismissBackendUpdate,
  }
}
