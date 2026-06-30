import { useCallback, useEffect, useRef, useState } from 'react'
import { useRegisterSW } from 'virtual:pwa-register/react'

export type PwaUpdateState = {
  swUpdateReady: boolean
  applying: boolean
  applySwUpdate: () => Promise<void>
  dismissSwUpdate: () => void
}

export function usePwaUpdate(): PwaUpdateState {
  const dismissedRef = useRef(false)
  const [swUpdateReady, setSwUpdateReady] = useState(false)
  const [applying, setApplying] = useState(false)

  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onNeedRefresh() {
      if (!dismissedRef.current) {
        setSwUpdateReady(true)
      }
    },
    onRegisteredSW(_swUrl, registration) {
      if (!registration) return
      window.setInterval(() => {
        if (!dismissedRef.current) {
          void registration.update()
        }
      }, 60 * 60 * 1000)
    },
  })

  useEffect(() => {
    if (needRefresh && !dismissedRef.current) {
      setSwUpdateReady(true)
    }
  }, [needRefresh])

  const applySwUpdate = useCallback(async () => {
    setApplying(true)
    dismissedRef.current = false
    try {
      await updateServiceWorker(true)
    } finally {
      setApplying(false)
    }
  }, [updateServiceWorker])

  const dismissSwUpdate = useCallback(() => {
    dismissedRef.current = true
    setSwUpdateReady(false)
    setNeedRefresh(false)
  }, [setNeedRefresh])

  return { swUpdateReady, applying, applySwUpdate, dismissSwUpdate }
}
