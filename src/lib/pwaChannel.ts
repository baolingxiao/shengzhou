/** PWA / 桌面渠道辅助 */

const DEFAULT_UPDATE_INTERVAL_MS = 3600 * 1000

export function getSettingsIntervalMs(): number {
  const raw = import.meta.env.VITE_UPDATE_CHECK_INTERVAL_SECONDS
  if (!raw) return DEFAULT_UPDATE_INTERVAL_MS
  const sec = Number.parseInt(String(raw), 10)
  if (!Number.isFinite(sec) || sec < 300) return DEFAULT_UPDATE_INTERVAL_MS
  return sec * 1000
}

export function isPwaChannel(): boolean {
  if (typeof window === 'undefined') return false
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true ||
    import.meta.env.VITE_APP_CHANNEL === 'pwa'
  )
}
