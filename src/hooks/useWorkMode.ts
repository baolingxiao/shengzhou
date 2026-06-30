import { useCallback, useEffect, useState } from 'react'
import { DEFAULT_CHARACTER_ID, DEFAULT_SESSION_ID } from '../lib/characterConfig'
import { fetchWorkMode, type WorkModeSnapshot } from '../lib/workModeApi'

export function useWorkMode(enabled: boolean, sessionId = DEFAULT_SESSION_ID) {
  const [snapshot, setSnapshot] = useState<WorkModeSnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!enabled) return
    try {
      const data = await fetchWorkMode(sessionId, DEFAULT_CHARACTER_ID)
      setSnapshot(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法加载上下班状态')
    }
  }, [enabled, sessionId])

  useEffect(() => {
    if (!enabled) return
    void reload()
    const timer = window.setInterval(() => void reload(), 30_000)
    return () => window.clearInterval(timer)
  }, [enabled, reload])

  return { snapshot, error, reload }
}
