/**
 * Execution Trace — 前端 trace_id 生成、传递与客户端事件上报。
 */

export type ClientTracePatch = {
  trace_id: string
  pipeline?: {
    frontend?: {
      request_sent_at?: string
      response_received_at?: string
      response_ms?: number
      tts_triggered?: boolean
    }
  }
  tts?: {
    enabled?: boolean
    chunks?: Array<{
      index: number
      text?: string
      request_ms?: number
      audio_duration_ms?: number
      played?: boolean
      play_start_at?: string
      play_end_at?: string
    }>
  }
  errors?: Array<{ step: string; error: string; at?: string }>
}

let activeTraceId: string | null = null

export function newTraceId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `trace-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function beginTrace(userInput: string): string {
  const traceId = newTraceId()
  activeTraceId = traceId
  console.log('[TRACE]', traceId, userInput.slice(0, 60))
  return traceId
}

export function getActiveTraceId(): string | null {
  return activeTraceId
}

export function clearActiveTrace(): void {
  activeTraceId = null
}

export function traceHeaders(traceId: string | null): Record<string, string> {
  if (!traceId) return {}
  return { 'X-Trace-Id': traceId }
}

export async function patchClientTrace(patch: ClientTracePatch): Promise<void> {
  try {
    await fetch('/api/trace/client', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
  } catch (err) {
    console.warn('[TRACE] client patch failed', err)
  }
}

export function isoNow(): string {
  return new Date().toISOString()
}
