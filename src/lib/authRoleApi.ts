import { API_BASE } from './chatApi'
import { authHeaders } from './authSession'

/** 查询后端管理者身份；接口不可用时返回 null，由登录 session 兜底。 */
export async function fetchAuthRole(username: string): Promise<boolean | null> {
  try {
    const q = new URLSearchParams({ username: username.trim() })
    const resp = await fetch(`${API_BASE}/auth/role?${q}`, {
      headers: authHeaders(),
    })
    if (!resp.ok) return null
    const body = (await resp.json()) as { is_admin?: boolean }
    return Boolean(body.is_admin)
  } catch {
    return null
  }
}
