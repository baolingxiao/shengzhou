export type LoginResult = {
  ok: boolean
  username: string
  role: 'developer' | 'user'
  is_admin: boolean
  access_token: string
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
    if (resp.status === 404) {
      throw new Error('登录接口不可用，请重启后端服务')
    }
    if (resp.status === 405 && url.includes('/api/register')) {
      throw new Error('后端尚未更新到注册版本，请先更新并重启服务')
    }
    if (resp.status === 401) {
      throw new Error('用户名或密码错误')
    }
    throw new Error(detail || `请求失败 (${resp.status})`)
  }
  return resp.json() as Promise<T>
}

export async function login(username: string, password: string): Promise<LoginResult> {
  return requestJson<LoginResult>('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}

export async function register(username: string, password: string): Promise<LoginResult> {
  return requestJson<LoginResult>('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}
