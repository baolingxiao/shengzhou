import { useEffect, useState } from 'react'
import { fetchAuthRole } from '../lib/authRoleApi'

/**
 * 管理者判定：优先后端 `/api/auth/role` 校验；
 * 接口缺失或离线时回退到登录 session 中的 isAdmin。
 */
export function useAdminRole(
  username: string | null,
  sessionIsAdmin: boolean,
  enabled = true,
) {
  const [remoteAdmin, setRemoteAdmin] = useState<boolean | null>(null)

  useEffect(() => {
    if (!enabled || !username?.trim()) {
      setRemoteAdmin(null)
      return
    }

    let cancelled = false
    void fetchAuthRole(username).then((role) => {
      if (!cancelled) setRemoteAdmin(role)
    })

    return () => {
      cancelled = true
    }
  }, [enabled, username])

  return remoteAdmin ?? sessionIsAdmin
}
