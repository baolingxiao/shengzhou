const BASE = '/api/system'

export type PermissionItem = {
  granted: boolean
  required: boolean
  label?: string
  detail?: string
  probe?: string
}

export type PermissionsSnapshot = {
  platform: string
  agent_control_available: boolean
  running_in_app?: boolean
  allow_terminal_agent?: boolean
  tcc_identity?: string
  system_permissions_granted?: boolean
  needs_app_restart?: boolean
  backend_process_path?: string
  backend_process_name?: string
  app_bundle_path?: string
  bundle_name?: string
  code_signing?: {
    stable?: boolean
    kind?: string
    detail?: string
    designated_requirement?: string
  }
  tcc_cdhash_mismatch_suspected?: boolean
  accessibility: PermissionItem
  screen_recording: PermissionItem
  all_granted: boolean
  message: string
  checked_at?: string
}

export type AppVersionInfo = {
  app_name: string
  version: string
  build_id: string
  git_rev: string
  git_branch: string
  channel: string
}

export type UpdateCheckResult = AppVersionInfo & {
  update_available: boolean
  check_enabled: boolean
  remote_rev: string
  commits_behind: number
  summary: string
  dismissed_build_id: string
}

export async function fetchPermissions(force = false): Promise<PermissionsSnapshot> {
  const q = force ? '?force=1' : ''
  const res = await fetch(`${BASE}/permissions${q}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`权限检测失败 (${res.status})`)
  return res.json() as Promise<PermissionsSnapshot>
}

export async function openPermissionSettings(
  kind: 'accessibility' | 'screen_recording',
): Promise<void> {
  const res = await fetch(`${BASE}/permissions/open`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind }),
  })
  if (!res.ok) throw new Error(`打开系统设置失败 (${res.status})`)
}

export async function fetchAppVersion(): Promise<AppVersionInfo> {
  const res = await fetch(`${BASE}/version`)
  if (!res.ok) throw new Error(`版本信息失败 (${res.status})`)
  return res.json() as Promise<AppVersionInfo>
}

export async function checkAppUpdate(force = false): Promise<UpdateCheckResult> {
  const q = force ? '?force=1' : ''
  const res = await fetch(`${BASE}/update/check${q}`)
  if (!res.ok) throw new Error(`更新检测失败 (${res.status})`)
  return res.json() as Promise<UpdateCheckResult>
}

export async function dismissAppUpdate(buildId: string): Promise<void> {
  const res = await fetch(`${BASE}/update/dismiss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ build_id: buildId }),
  })
  if (!res.ok) throw new Error(`推迟更新失败 (${res.status})`)
}

export async function applyAppUpdate(): Promise<{
  ok: boolean
  message: string
  steps?: string[]
}> {
  const res = await fetch(`${BASE}/update/apply`, { method: 'POST' })
  const data = (await res.json()) as { ok: boolean; message: string; steps?: string[] }
  if (!res.ok && !data.message) throw new Error(`应用更新失败 (${res.status})`)
  return data
}

export async function requestAutoPermissionSetup(): Promise<{
  all_granted: boolean
  message: string
  steps: Array<{ kind: string; ok?: boolean; granted?: boolean; method?: string; user_action?: string }>
  snapshot?: PermissionsSnapshot
}> {
  const res = await fetch(`${BASE}/permissions/auto-setup`, { method: 'POST' })
  if (!res.ok) throw new Error(`一键授权失败 (${res.status})`)
  return res.json() as Promise<{
    all_granted: boolean
    message: string
    steps: Array<{ kind: string; ok?: boolean; granted?: boolean; method?: string; user_action?: string }>
    snapshot?: PermissionsSnapshot
  }>
}

export function isPwaStandalone(): boolean {
  if (typeof window === 'undefined') return false
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  )
}
