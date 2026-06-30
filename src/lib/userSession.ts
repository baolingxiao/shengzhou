import { DEFAULT_SESSION_ID } from './characterConfig'

/** 登录用户名即用户 ID（与后端记忆会话一一对应） */
export function resolveUserId(username: string): string {
  return username.trim()
}

/** 将用户 ID 映射为独立的对话 / 记忆 session_id */
export function resolveSessionId(username: string | null | undefined): string {
  if (!username?.trim()) return DEFAULT_SESSION_ID
  const safe = username.trim().replace(/[^\w\-.]/g, '_').slice(0, 80)
  return safe ? `user-${safe}` : DEFAULT_SESSION_ID
}
