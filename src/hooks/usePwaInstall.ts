import { useCallback, useEffect, useRef, useState } from 'react'
import { isPwaChannel } from '../lib/pwaChannel'

const DISMISS_KEY = 'jarvis_pwa_install_dismissed'

export type PwaInstallMode =
  | 'native'
  | 'safari_ios'
  | 'safari_mac'
  | 'chrome_manual'
  | 'insecure'
  | 'unavailable'

export type PwaInstallState = {
  shouldPrompt: boolean
  mode: PwaInstallMode
  installing: boolean
  applyInstall: () => Promise<void>
  dismissInstall: () => void
}

function isLocalDevHost(hostname: string): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1'
}

function isSecureContext(): boolean {
  if (typeof window === 'undefined') return false
  return window.isSecureContext || window.location.protocol === 'https:'
}

function isIosSafari(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  const ios = /iPad|iPhone|iPod/.test(ua)
  const ipadOs =
    navigator.platform === 'MacIntel' && typeof navigator.maxTouchPoints === 'number'
      ? navigator.maxTouchPoints > 1
      : false
  return (ios || ipadOs) && /Safari/i.test(ua) && !/CriOS|FxiOS|EdgiOS/i.test(ua)
}

function isMacSafari(): boolean {
  if (typeof navigator === 'undefined') return false
  return (
    /Macintosh/.test(navigator.userAgent) &&
    /Safari/i.test(navigator.userAgent) &&
    !/Chrome|Chromium|Edg|OPR/i.test(navigator.userAgent)
  )
}

function detectManualMode(): PwaInstallMode | null {
  if (isIosSafari()) return 'safari_ios'
  if (isMacSafari()) return 'safari_mac'
  return null
}

export function usePwaInstall(): PwaInstallState {
  const deferredRef = useRef<BeforeInstallPromptEvent | null>(null)
  const [nativeReady, setNativeReady] = useState(false)
  const [manualMode, setManualMode] = useState<PwaInstallMode | null>(null)
  const [installing, setInstalling] = useState(false)
  const [dismissed, setDismissed] = useState(
    () => typeof localStorage !== 'undefined' && localStorage.getItem(DISMISS_KEY) === '1',
  )

  const eligibleHost = (() => {
    if (typeof window === 'undefined') return false
    if (isPwaChannel()) return false
    if (isLocalDevHost(window.location.hostname)) return false
    return true
  })()

  useEffect(() => {
    if (!eligibleHost) return

    const onBeforeInstall = (event: BeforeInstallPromptEvent) => {
      event.preventDefault()
      deferredRef.current = event
      setNativeReady(true)
      setManualMode(null)
    }

    const onInstalled = () => {
      deferredRef.current = null
      setNativeReady(false)
      setManualMode(null)
      localStorage.removeItem(DISMISS_KEY)
      setDismissed(false)
    }

    window.addEventListener('beforeinstallprompt', onBeforeInstall)
    window.addEventListener('appinstalled', onInstalled)

    const timer = window.setTimeout(() => {
      if (deferredRef.current) return
      if (!isSecureContext()) {
        setManualMode('insecure')
        return
      }
      const manual = detectManualMode()
      if (manual) {
        setManualMode(manual)
        return
      }
      if (/Chrome|Chromium|Edg/i.test(navigator.userAgent)) {
        setManualMode('chrome_manual')
      }
    }, 2500)

    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('beforeinstallprompt', onBeforeInstall)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [eligibleHost])

  const mode: PwaInstallMode = nativeReady
    ? 'native'
    : manualMode ?? 'unavailable'

  const shouldPrompt = Boolean(
    eligibleHost &&
      !dismissed &&
      !isPwaChannel() &&
      (nativeReady || manualMode !== null),
  )

  const applyInstall = useCallback(async () => {
    const prompt = deferredRef.current
    if (!prompt) return
    setInstalling(true)
    try {
      await prompt.prompt()
      const choice = await prompt.userChoice
      deferredRef.current = null
      setNativeReady(false)
      if (choice.outcome === 'accepted') {
        localStorage.removeItem(DISMISS_KEY)
        setDismissed(false)
      }
    } finally {
      setInstalling(false)
    }
  }, [])

  const dismissInstall = useCallback(() => {
    localStorage.setItem(DISMISS_KEY, '1')
    setDismissed(true)
  }, [])

  return {
    shouldPrompt,
    mode,
    installing,
    applyInstall,
    dismissInstall,
  }
}
