import { API_BASE } from './chatApi'
import { DEFAULT_CHARACTER_ID, DEFAULT_SESSION_ID } from './characterConfig'
import { authHeaders } from './authSession'

export type MemoryTier = 'short' | 'medium' | 'long'

export type MemoryItem = {
  id: string
  tier: MemoryTier
  tier_label: string
  rel_path: string
  title: string
  date_label: string
  preview: string
  marked: boolean
  modified_at: number
  category: string
}

export type ChatHistoryMessage = {
  role: 'user' | 'assistant'
  content: string
}

async function adminJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: authHeaders({
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function fetchMemorySummary(characterId = DEFAULT_CHARACTER_ID) {
  return adminJson<{
    character: string
    counts: Record<MemoryTier, number>
    maintenance_hint: string
  }>(`/admin/memory/summary?character_id=${encodeURIComponent(characterId)}`)
}

export async function fetchMemoryList(tier: MemoryTier, characterId = DEFAULT_CHARACTER_ID) {
  return adminJson<{ items: MemoryItem[] }>(
    `/admin/memory?tier=${tier}&character_id=${encodeURIComponent(characterId)}`,
  )
}

export async function fetchMemoryDetail(relPath: string, characterId = DEFAULT_CHARACTER_ID) {
  return adminJson<{ title: string; body: string; category: string }>(
    `/admin/memory/detail?rel_path=${encodeURIComponent(relPath)}&character_id=${encodeURIComponent(characterId)}`,
  )
}

export async function deleteMemory(relPath: string, characterId = DEFAULT_CHARACTER_ID) {
  return adminJson<{ ok: boolean }>('/admin/memory', {
    method: 'DELETE',
    body: JSON.stringify({ character_id: characterId, rel_path: relPath }),
  })
}

export async function toggleMemoryMark(relPath: string, characterId = DEFAULT_CHARACTER_ID) {
  return adminJson<{ ok: boolean; marked: boolean }>('/admin/memory/mark', {
    method: 'POST',
    body: JSON.stringify({ character_id: characterId, rel_path: relPath }),
  })
}

export async function runMemoryMaintenance(
  action: 'daily' | 'weekly' | 'monthly' | 'catchup',
  dryRun = false,
  characterId = DEFAULT_CHARACTER_ID,
) {
  return adminJson<{ result: unknown }>('/admin/memory/maintenance', {
    method: 'POST',
    body: JSON.stringify({ character_id: characterId, action, dry_run: dryRun }),
  })
}

export async function optimizeMemoryTitles(characterId = DEFAULT_CHARACTER_ID, limit = 24) {
  return adminJson<{ updated: number }>(
    `/admin/memory/titles?character_id=${encodeURIComponent(characterId)}&limit=${limit}`,
    { method: 'POST' },
  )
}

export async function deleteMemoryMessages(
  indices: number[],
  opts: { relPath?: string; sessionId?: string; characterId?: string } = {},
) {
  return adminJson<{ result: { deleted_count: number; remaining: number; file_removed?: boolean } }>(
    '/admin/memory/messages/delete',
    {
      method: 'POST',
      body: JSON.stringify({
        character_id: opts.characterId ?? DEFAULT_CHARACTER_ID,
        rel_path: opts.relPath,
        session_id: opts.sessionId,
        indices,
      }),
    },
  )
}

export async function fetchChatHistory(sessionId = DEFAULT_SESSION_ID) {
  return adminJson<{ messages: ChatHistoryMessage[]; count: number }>(
    `/admin/chat/history?session_id=${encodeURIComponent(sessionId)}`,
  )
}

export async function clearChatSession(sessionId = DEFAULT_SESSION_ID) {
  return adminJson<{ ok: boolean }>(
    `/admin/chat/session?session_id=${encodeURIComponent(sessionId)}`,
    { method: 'DELETE' },
  )
}
