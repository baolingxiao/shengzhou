import {
  DEFAULT_CHARACTER_ID,
  DEFAULT_SESSION_ID,
} from './characterConfig'
import { traceHeaders } from './executionTrace'
import { authHeaders } from './authSession'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
}

export type CharacterInfo = {
  id: string
  name: string
  ai_type: string
  user_mbti: string
}

export type ChatReply = {
  text: string
  route: string
  blocked: boolean
  work_mode?: string | null
  trust_delta?: number | null
  trust_points?: number | null
  segments?: string[] | null
  trace_id?: string | null
}

export const API_BASE = '/api'

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    ...init,
    headers: authHeaders(init?.headers),
  })
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail || `请求失败 (${resp.status})`)
  }
  return resp.json() as Promise<T>
}

export async function fetchCharacter(
  characterId = DEFAULT_CHARACTER_ID,
): Promise<CharacterInfo> {
  const q = new URLSearchParams({ character_id: characterId })
  return requestJson<CharacterInfo>(`${API_BASE}/character?${q}`)
}

export async function sendChatMessage(
  text: string,
  sessionId = DEFAULT_SESSION_ID,
  characterId = DEFAULT_CHARACTER_ID,
  traceId?: string | null,
): Promise<ChatReply> {
  const sentAt = new Date().toISOString()
  const t0 = performance.now()
  const reply = await requestJson<ChatReply>(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...traceHeaders(traceId ?? null),
    },
    body: JSON.stringify({
      text,
      session_id: sessionId,
      character_id: characterId,
      trace_id: traceId ?? undefined,
    }),
  })
  const responseMs = Math.round(performance.now() - t0)
  const resolvedTraceId = reply.trace_id ?? traceId
  if (resolvedTraceId) {
    console.log('[TRACE]', resolvedTraceId, `response_ms=${responseMs}`)
    const { patchClientTrace } = await import('./executionTrace')
    void patchClientTrace({
      trace_id: resolvedTraceId,
      pipeline: {
        frontend: {
          request_sent_at: sentAt,
          response_received_at: new Date().toISOString(),
          response_ms: responseMs,
        },
      },
    })
  }
  return reply
}

export async function resetChatSession(sessionId = DEFAULT_SESSION_ID): Promise<void> {
  await requestJson<{ ok: boolean }>(`${API_BASE}/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  })
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${API_BASE}/health`)
    return resp.ok
  } catch {
    return false
  }
}
