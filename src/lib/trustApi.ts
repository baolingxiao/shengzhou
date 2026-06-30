import { API_BASE } from './chatApi'
import { DEFAULT_CHARACTER_ID } from './characterConfig'

export type TrustSnapshot = {
  character_id: string
  character: string
  display_name: string
  trust_points: number
  min: number
  max: number
  level: number
  level_name: string
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init)
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

export async function fetchTrust(characterId = DEFAULT_CHARACTER_ID): Promise<TrustSnapshot> {
  const q = new URLSearchParams({ character_id: characterId })
  return requestJson<TrustSnapshot>(`${API_BASE}/trust?${q}`)
}

export async function updateTrustPoints(
  trustPoints: number,
  username: string,
  characterId = DEFAULT_CHARACTER_ID,
): Promise<TrustSnapshot> {
  return requestJson<TrustSnapshot>(`${API_BASE}/admin/trust`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      character_id: characterId,
      trust_points: trustPoints,
      username,
    }),
  })
}
