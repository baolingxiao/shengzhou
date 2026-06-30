import { API_BASE } from './chatApi'
import { authHeaders } from './authSession'

export type UserPersona = {
  display_name: string
  style_prompt: string
  chatgpt_api_key: string
  claude_api_key: string
  deepseek_api_key: string
  doubao_api_key: string
  updated_at: string
}

export type UserPersonaApiKeys = {
  chatgptApiKey: string
  claudeApiKey: string
  deepseekApiKey: string
  doubaoApiKey: string
}

export type UserPersonaState = {
  ok: boolean
  required: boolean
  configured: boolean
  persona: UserPersona | null
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

export async function fetchUserPersona(): Promise<UserPersonaState> {
  return requestJson<UserPersonaState>(`${API_BASE}/user/persona`, {
    headers: authHeaders(),
  })
}

export async function saveUserPersona(
  displayName: string,
  stylePrompt: string,
  apiKeys: UserPersonaApiKeys,
): Promise<UserPersonaState> {
  return requestJson<UserPersonaState>(`${API_BASE}/user/persona`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      display_name: displayName,
      style_prompt: stylePrompt,
      chatgpt_api_key: apiKeys.chatgptApiKey,
      claude_api_key: apiKeys.claudeApiKey,
      deepseek_api_key: apiKeys.deepseekApiKey,
      doubao_api_key: apiKeys.doubaoApiKey,
    }),
  })
}

