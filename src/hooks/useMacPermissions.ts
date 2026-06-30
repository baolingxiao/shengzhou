import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchPermissions,
  openPermissionSettings,
  requestAutoPermissionSetup,
  type PermissionsSnapshot,
} from '../lib/systemApi'

const DISMISS_KEY = 'jarvis_permissions_reminder_dismissed'
const GRANTED_ACK_KEY = 'jarvis_permissions_granted_ack'

export type RecheckFeedback =
  | { status: 'idle' }
  | { status: 'checking' }
  | { status: 'requesting'; message: string }
  | { status: 'success'; message: string; at: string }
  | { status: 'partial'; message: string; at: string; missing: string[] }
  | { status: 'error'; message: string; at: string }

export type MacPermissionsState = {
  snapshot: PermissionsSnapshot | null
  loading: boolean
  rechecking: boolean
  autoSettingUp: boolean
  recheckFeedback: RecheckFeedback
  shouldPrompt: boolean
  showSuccessCelebration: boolean
  openSettings: (kind: 'accessibility' | 'screen_recording') => Promise<void>
  refresh: () => Promise<PermissionsSnapshot | null>
  dismissReminder: () => void
  recheckAfterSettings: () => Promise<void>
  runAutoSetup: () => Promise<void>
  clearRecheckFeedback: () => void
}

function missingLabels(data: PermissionsSnapshot): string[] {
  const out: string[] = []
  if (!data.accessibility.granted) out.push(data.accessibility.label ?? '辅助功能')
  if (!data.screen_recording.granted) out.push(data.screen_recording.label ?? '屏幕录制')
  return out
}

function formatTime(d = new Date()) {
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function sleep(ms: number) {
  return new Promise((r) => window.setTimeout(r, ms))
}

export function useMacPermissions(agentEnabled = true): MacPermissionsState {
  const [snapshot, setSnapshot] = useState<PermissionsSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [rechecking, setRechecking] = useState(false)
  const [autoSettingUp, setAutoSettingUp] = useState(false)
  const [recheckFeedback, setRecheckFeedback] = useState<RecheckFeedback>({ status: 'idle' })
  const [showSuccessCelebration, setShowSuccessCelebration] = useState(false)
  const [dismissed, setDismissed] = useState(
    () => typeof localStorage !== 'undefined' && localStorage.getItem(DISMISS_KEY) === '1',
  )
  const pollRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const applySnapshot = useCallback((data: PermissionsSnapshot) => {
    setSnapshot(data)
    if (data.all_granted) {
      localStorage.removeItem(DISMISS_KEY)
      localStorage.setItem(GRANTED_ACK_KEY, '1')
      setDismissed(false)
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchPermissions(true)
      applySnapshot(data)
      return data
    } catch {
      setSnapshot(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [applySnapshot])

  const finishIfGranted = useCallback(
    (data: PermissionsSnapshot) => {
      if (!data.all_granted) return false
      stopPolling()
      return true
    },
    [stopPolling],
  )

  const recheckAfterSettings = useCallback(async () => {
    setRechecking(true)
    setRecheckFeedback({ status: 'checking' })
    setShowSuccessCelebration(false)

    const started = Date.now()
    try {
      const data = await fetchPermissions(true)
      const elapsed = Date.now() - started
      if (elapsed < 700) await sleep(700 - elapsed)

      if (!data) {
        setRecheckFeedback({
          status: 'error',
          message: '无法连接后端，请确认贾维斯已启动。',
          at: formatTime(),
        })
        return
      }

      applySnapshot(data)
      if (finishIfGranted(data)) return

      const missing = missingLabels(data)
      setRecheckFeedback({
        status: 'partial',
        message: data.needs_app_restart
          ? '系统设置里若已打开「贾维斯」辅助功能，请按 ⌘Q 完全退出后重新打开 App。'
          : `还差 ${missing.join('、')}。若系统设置已打开，请打开开关；贾维斯会继续自动检测。`,
        at: formatTime(),
        missing,
      })
    } catch (e) {
      setRecheckFeedback({
        status: 'error',
        message: e instanceof Error ? e.message : '检测失败，请稍后重试。',
        at: formatTime(),
      })
    } finally {
      setRechecking(false)
    }
  }, [applySnapshot, finishIfGranted])

  const startPolling = useCallback(() => {
    stopPolling()
    let rounds = 0
    pollRef.current = window.setInterval(() => {
      rounds += 1
      void recheckAfterSettings()
      if (rounds >= 25) stopPolling()
    }, 2000)
  }, [recheckAfterSettings, stopPolling])

  const runAutoSetup = useCallback(async () => {
    setAutoSettingUp(true)
    setRecheckFeedback({
      status: 'requesting',
      message: '正在唤起 macOS 系统授权…请留意屏幕上的系统弹窗或「系统设置」。',
    })
    try {
      const result = await requestAutoPermissionSetup()
      if (result.snapshot) applySnapshot(result.snapshot)

      if (result.all_granted || result.snapshot?.all_granted) {
        if (result.snapshot) finishIfGranted(result.snapshot)
        return
      }

      setRecheckFeedback({
        status: 'partial',
        message: result.message || '请在系统弹窗中点「允许」或打开开关，贾维斯会自动检测…',
        at: formatTime(),
        missing: result.snapshot ? missingLabels(result.snapshot) : [],
      })
      startPolling()
    } catch (e) {
      setRecheckFeedback({
        status: 'error',
        message: e instanceof Error ? e.message : '一键授权失败',
        at: formatTime(),
      })
    } finally {
      setAutoSettingUp(false)
    }
  }, [applySnapshot, finishIfGranted, startPolling])

  useEffect(() => {
    if (!agentEnabled) return
    void refresh()
    const id = window.setInterval(() => void refresh(), 30_000)
    return () => {
      window.clearInterval(id)
      stopPolling()
    }
  }, [agentEnabled, refresh, stopPolling])

  // 不再自动唤起 macOS 系统弹窗；仅由用户点击「一键授权」时触发

  const openSettings = useCallback(async (kind: 'accessibility' | 'screen_recording') => {
    await openPermissionSettings(kind)
    startPolling()
  }, [startPolling])

  const dismissReminder = useCallback(() => {
    localStorage.setItem(DISMISS_KEY, '1')
    setDismissed(true)
    setRecheckFeedback({ status: 'idle' })
    setShowSuccessCelebration(false)
    stopPolling()
  }, [stopPolling])

  const clearRecheckFeedback = useCallback(() => {
    setRecheckFeedback({ status: 'idle' })
  }, [])

  const shouldPrompt = Boolean(
    agentEnabled &&
      snapshot &&
      snapshot.platform === 'Darwin' &&
      !dismissed &&
      !snapshot.all_granted &&
      !snapshot.system_permissions_granted &&
      !snapshot.needs_app_restart &&
      localStorage.getItem(GRANTED_ACK_KEY) !== '1',
  )

  return {
    snapshot,
    loading,
    rechecking,
    autoSettingUp,
    recheckFeedback,
    shouldPrompt,
    showSuccessCelebration,
    openSettings,
    refresh,
    dismissReminder,
    recheckAfterSettings,
    runAutoSetup,
    clearRecheckFeedback,
  }
}
