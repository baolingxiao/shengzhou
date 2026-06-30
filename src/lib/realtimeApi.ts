export type RealtimeSessionResponse = {
  client_secret: string
  model: string
  voice: string
  expires_at: string
  session_id: string
}

const API_BASE = '/api'

export async function createRealtimeSession(params: {
  characterId: string
  sessionId: string
  mode?: string
}): Promise<RealtimeSessionResponse> {
  const resp = await fetch(`${API_BASE}/realtime/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      character_id: params.characterId,
      session_id: params.sessionId,
      mode: params.mode ?? 'voice_chat',
    }),
  })
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Realtime 会话创建失败 (${resp.status})`)
  }
  const data = (await resp.json()) as RealtimeSessionResponse
  return data
}
