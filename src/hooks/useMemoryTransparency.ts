import { useCallback } from 'react'
import { fetchMemoryTransparency, type MemoryTransparencyRecord } from '../lib/adminApi'
import { DEFAULT_CHARACTER_ID } from '../lib/characterConfig'

/** 根据本轮 user 文本与 assistant 回复，从透明化日志中匹配最近一条记录。 */
export function matchTransparencyRecord(
  records: MemoryTransparencyRecord[],
  userText: string,
  replyText: string,
): MemoryTransparencyRecord | null {
  const u = userText.trim()
  const r = replyText.trim().slice(0, 240)
  if (!u && !r) return null

  for (let i = records.length - 1; i >= 0; i -= 1) {
    const row = records[i]
    if (!row) continue
    const queryMatch = row.user_query.trim() === u || row.user_query.includes(u) || u.includes(row.user_query.trim())
    const replyMatch =
      !r ||
      !row.reply_preview ||
      row.reply_preview.trim().startsWith(r.slice(0, 80)) ||
      r.startsWith(row.reply_preview.trim().slice(0, 80))
    if (queryMatch && replyMatch) return row
  }

  return records.length > 0 ? (records[records.length - 1] ?? null) : null
}

export function useMemoryTransparencyAttach(sessionId: string) {
  const attachToLastAssistant = useCallback(
    async (
      userText: string,
      assistantText: string,
    ): Promise<{ memoryIds: string[]; reasoning?: string } | null> => {
      try {
        const res = await fetchMemoryTransparency(sessionId, DEFAULT_CHARACTER_ID)
        const row = matchTransparencyRecord(res.records, userText, assistantText)
        if (!row || row.memory_ids.length === 0) return null
        return { memoryIds: row.memory_ids, reasoning: row.reasoning || undefined }
      } catch {
        return null
      }
    },
    [sessionId],
  )

  return { attachToLastAssistant }
}
