import { API_BASE } from './chatApi'
import { DEFAULT_CHARACTER_ID, DEFAULT_SESSION_ID } from './characterConfig'

export type WorkModeSnapshot = {
  mode: 'work' | 'companion' | 'overtime'
  mode_label: string
  agent_tools_allowed: boolean
  is_workday: boolean
  clock: string
  work_window: string
  timezone: string
  awaiting_overtime_consent: boolean
  has_deferred_task: boolean
  overtime_active: boolean
  overtime_tp_cost: number
  work_start?: string
  work_end?: string
}

export async function fetchWorkMode(
  sessionId = DEFAULT_SESSION_ID,
  characterId = DEFAULT_CHARACTER_ID,
): Promise<WorkModeSnapshot> {
  const q = new URLSearchParams({
    session_id: sessionId,
    character_id: characterId,
  })
  const resp = await fetch(`${API_BASE}/system/work-mode?${q}`)
  if (!resp.ok) {
    throw new Error('无法加载上下班状态')
  }
  return resp.json() as Promise<WorkModeSnapshot>
}
