import { useCallback, useState } from 'react'

export type BackgroundMode = 'solid' | 'ocean'

const STORAGE_KEY = 'neuralpal-bg-mode'

function readStored(): BackgroundMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'solid' || v === 'ocean') return v
  } catch {
    /* ignore */
  }
  return 'ocean'
}

export function useBackgroundMode() {
  const [mode, setMode] = useState<BackgroundMode>(readStored)

  const toggle = useCallback(() => {
    setMode((prev) => {
      const next: BackgroundMode = prev === 'ocean' ? 'solid' : 'ocean'
      try {
        localStorage.setItem(STORAGE_KEY, next)
      } catch {
        /* ignore */
      }
      return next
    })
  }, [])

  return { mode, toggle, isOcean: mode === 'ocean', isSolid: mode === 'solid' }
}
