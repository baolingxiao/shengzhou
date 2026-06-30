import { useCallback, useEffect, useState } from 'react'
import type { AuthSession } from '../lib/authSession'
import {
  fetchUserPersona,
  saveUserPersona,
  type UserPersona,
  type UserPersonaApiKeys,
} from '../lib/userPersonaApi'

function hasAnyApiKey(persona: UserPersona | null | undefined): boolean {
  return Boolean(
    persona?.chatgpt_api_key?.trim() ||
    persona?.claude_api_key?.trim() ||
    persona?.deepseek_api_key?.trim() ||
    persona?.doubao_api_key?.trim(),
  )
}

export function useUserPersona(session: AuthSession | null) {
  const [persona, setPersona] = useState<UserPersona | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const required = session?.role === 'user'
  const configured = !required || (
    persona?.display_name?.trim() &&
    persona?.style_prompt?.trim() &&
    hasAnyApiKey(persona)
  )

  const reload = useCallback(async () => {
    if (!session || session.role !== 'user') {
      setPersona(null)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const state = await fetchUserPersona()
      setPersona(state.persona)
    } catch (err) {
      setError(err instanceof Error ? err.message : '读取角色配置失败')
      setPersona(null)
    } finally {
      setLoading(false)
    }
  }, [session])

  useEffect(() => {
    void reload()
  }, [reload])

  const save = useCallback(async (
    displayName: string,
    stylePrompt: string,
    apiKeys: UserPersonaApiKeys,
  ) => {
    if (!session || session.role !== 'user') return
    setSaving(true)
    setError(null)
    try {
      const state = await saveUserPersona(displayName, stylePrompt, apiKeys)
      setPersona(state.persona)
    } catch (err) {
      const message = err instanceof Error ? err.message : '保存角色配置失败'
      setError(message)
      throw err
    } finally {
      setSaving(false)
    }
  }, [session])

  return {
    persona,
    loading,
    saving,
    error,
    required,
    configured: Boolean(configured),
    reload,
    save,
  }
}

