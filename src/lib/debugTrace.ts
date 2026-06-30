/**
 * Dev-only checkpoints → POST /api/debug/trace → backend terminal stdout.
 * Reproduce the bug, then copy terminal lines between [JARVIS-TRACE] markers.
 */

let seq = 0
let loadCount = 0

function sessionId(): string {
  const key = 'jarvis-debug-session'
  let id = sessionStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID().slice(0, 8)
    sessionStorage.setItem(key, id)
  }
  return id
}

function bumpLoadCount(): number {
  const key = 'jarvis-debug-load-count'
  loadCount = Number(sessionStorage.getItem(key) || '0') + 1
  sessionStorage.setItem(key, String(loadCount))
  return loadCount
}

export function trace(
  checkpoint: string,
  detail: Record<string, unknown> = {},
  level: 'info' | 'warn' | 'alert' = 'info',
) {
  if (!import.meta.env.DEV) return

  seq += 1
  const payload = {
    seq,
    level,
    session: sessionId(),
    checkpoint,
    url: location.href,
    loadCount: loadCount || Number(sessionStorage.getItem('jarvis-debug-load-count') || '0'),
    ts: new Date().toISOString(),
    ...detail,
  }

  const line = `[jarvis-trace] #${seq} ${checkpoint}`
  if (level === 'alert') {
    console.error(line, detail)
  } else if (level === 'warn') {
    console.warn(line, detail)
  } else {
    console.log(line, detail)
  }

  void fetch('/api/debug/trace', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {
    /* backend may be offline */
  })
}

export function traceStateChange(
  checkpoint: string,
  field: string,
  from: unknown,
  to: unknown,
  extra: Record<string, unknown> = {},
) {
  if (from === to) return
  const level =
    field === 'bootPhase' && to === 'awaiting-start' && from === 'running'
      ? 'alert'
      : field === 'chatUnlocked' && to === false && from === true
        ? 'alert'
        : 'info'
  trace(
    checkpoint,
    { field, from, to, ...extra },
    level,
  )
}

export function installGlobalTraceHooks() {
  if (!import.meta.env.DEV) return

  trace('app.page_load', {
    loadCount: bumpLoadCount(),
    navType: performance.getEntriesByType('navigation')[0]
      ? (performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming).type
      : 'unknown',
    userAgent: navigator.userAgent.slice(0, 80),
  })

  window.addEventListener('beforeunload', () => {
    trace('app.beforeunload', {}, 'warn')
  })

  window.addEventListener('pagehide', (e) => {
    trace('app.pagehide', { persisted: e.persisted }, 'warn')
  })

  window.addEventListener('error', (e) => {
    trace(
      'app.window_error',
      { message: e.message, filename: e.filename, lineno: e.lineno },
      'alert',
    )
  })

  window.addEventListener('unhandledrejection', (e) => {
    trace(
      'app.unhandled_rejection',
      { reason: String(e.reason) },
      'alert',
    )
  })
}
