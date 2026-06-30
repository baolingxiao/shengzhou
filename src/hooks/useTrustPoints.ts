import { useCallback, useEffect, useRef, useState } from 'react'
import { DEFAULT_CHARACTER_ID } from '../lib/characterConfig'
import type { ChatReply } from '../lib/chatApi'
import { fetchTrust, updateTrustPoints, type TrustSnapshot } from '../lib/trustApi'

export function useTrustPoints(enabled: boolean, isAdmin: boolean, username: string | null) {
  const [trust, setTrust] = useState<TrustSnapshot | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deltaFlash, setDeltaFlash] = useState<number | null>(null)
  const flashTimer = useRef<number | null>(null)

  const reload = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    try {
      const snapshot = await fetchTrust(DEFAULT_CHARACTER_ID)
      setTrust(snapshot)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法加载亲密度')
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    if (!enabled) return
    void reload()
  }, [enabled, reload])

  useEffect(() => {
    return () => {
      if (flashTimer.current !== null) {
        window.clearTimeout(flashTimer.current)
      }
    }
  }, [])

  const flashDelta = useCallback((delta: number) => {
    if (flashTimer.current !== null) {
      window.clearTimeout(flashTimer.current)
    }
    setDeltaFlash(delta)
    flashTimer.current = window.setTimeout(() => {
      setDeltaFlash(null)
      flashTimer.current = null
    }, 2200)
  }, [])

  const applyFromChatReply = useCallback(
    (reply: ChatReply) => {
      if (reply.trust_points == null) return
      setTrust((prev) =>
        prev
          ? {
              ...prev,
              trust_points: reply.trust_points!,
            }
          : {
              character_id: DEFAULT_CHARACTER_ID,
              character: '',
              display_name: '亲密度',
              trust_points: reply.trust_points!,
              min: 0,
              max: 100,
              level: 1,
              level_name: '',
            },
      )
      if (reply.trust_delta != null && reply.trust_delta !== 0) {
        flashDelta(reply.trust_delta)
      }
    },
    [flashDelta],
  )

  const setTrustPoints = useCallback(
    async (nextValue: number) => {
      if (!isAdmin || !username) return
      const clamped = Math.max(0, Math.min(100, Math.round(nextValue)))
      setTrust((prev) =>
        prev
          ? { ...prev, trust_points: clamped }
          : {
              character_id: DEFAULT_CHARACTER_ID,
              character: '',
              display_name: '亲密度',
              trust_points: clamped,
              min: 0,
              max: 100,
              level: 1,
              level_name: '',
            },
      )
      setSaving(true)
      try {
        const snapshot = await updateTrustPoints(clamped, username, DEFAULT_CHARACTER_ID)
        setTrust(snapshot)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : '更新亲密度失败')
        await reload()
      } finally {
        setSaving(false)
      }
    },
    [isAdmin, username, reload],
  )

  return {
    trust,
    loading,
    saving,
    error,
    reload,
    setTrustPoints,
    deltaFlash,
    applyFromChatReply,
  }
}
