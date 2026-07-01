import { motion, AnimatePresence } from 'motion/react'
import { cn } from '../../lib/cn'
import { useUserSession } from '../../contexts/UserSessionContext'
import { usePageLanguage } from '../../contexts/PageLanguageContext'
import { useAdminRole } from '../../hooks/useAdminRole'
import { useTrustPoints } from '../../hooks/useTrustPoints'
import { Panel } from '../ui/Panel'
import { IntimacyBar } from '../boot/IntimacyBar'

type UserProfilePageProps = {
  open: boolean
  onClose: () => void
  onLogout?: () => void
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M5 20c0-3.3 3.1-6 7-6s7 2.7 7 6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 border-b border-white/8 py-3 last:border-0">
      <span className="text-xs uppercase tracking-[0.12em] text-white/40">{label}</span>
      <span className="break-all font-mono text-sm text-[#f5f5f5]">{value}</span>
    </div>
  )
}

/** 用户信息页：展示用户 ID 与记忆会话绑定 */
export function UserProfilePage({ open, onClose, onLogout }: UserProfilePageProps) {
  const { username, userId, sessionId, loggedInAt, role, isAdmin: sessionIsAdmin } = useUserSession()
  const { language, setLanguage } = usePageLanguage()
  const isZh = language === 'zh'
  const isDeveloper = role === 'developer'
  const isAdmin = useAdminRole(username, sessionIsAdmin, open && isDeveloper)
  const {
    trust,
    saving: trustSaving,
    setTrustPoints,
    deltaFlash,
  } = useTrustPoints(open && isDeveloper, isAdmin, username)

  const copy = isZh
    ? {
        title: '用户信息',
        loggedIn: '已登录',
        loggedOut: '未登录',
        back: '返回',
        username: '用户名',
        userId: '用户 ID',
        sessionId: '记忆会话 ID',
        loginTime: '登录时间',
        loginRequired: '请先登录。不同用户 ID 拥有独立的 AI 对话记忆，互不影响。',
        sessionBinding: '记忆会话 ID 与当前用户绑定。切换账号后，沈昼将读取该用户专属的对话历史与短期记忆。',
        logout: '退出登录',
        close: '关闭',
      }
    : {
        title: 'User Profile',
        loggedIn: 'Signed in',
        loggedOut: 'Signed out',
        back: 'Back',
        username: 'Username',
        userId: 'User ID',
        sessionId: 'Memory Session ID',
        loginTime: 'Login Time',
        loginRequired:
          'Please sign in first. Each user ID has an isolated AI conversation memory, independent from others.',
        sessionBinding:
          "The memory session ID is bound to the current user. After switching accounts, Shenzhou reads that user's own conversation history and short-term memory.",
        logout: 'Sign out',
        close: 'Close',
      }

  const loggedInLabel =
    loggedInAt != null
      ? new Date(loggedInAt).toLocaleString(isZh ? 'zh-CN' : 'en-US', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        })
      : '—'

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-[#050505]/95 px-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          <motion.div
            className="w-full max-w-md"
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          >
            <Panel
              gradient
              className="border-white/15 bg-[#0a0a0c]/80 p-6 text-foreground shadow-2xl"
            >
              <div className="mb-6 flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'flex h-11 w-11 items-center justify-center rounded-full',
                      'border border-white/20 bg-white/8 text-white/80',
                    )}
                  >
                    <UserIcon className="h-5 w-5" />
                  </div>
                  <div>
                    <h1 className="text-lg font-medium tracking-tight text-[#f5f5f5]">{copy.title}</h1>
                    <p className="mt-0.5 text-sm text-white/45">
                      {username ? copy.loggedIn : copy.loggedOut}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      'inline-flex items-center gap-1 rounded-full border border-white/15 bg-white/5 p-1',
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => setLanguage('zh')}
                      className={cn(
                        'rounded-full px-2.5 py-1 text-xs transition-colors',
                        language === 'zh'
                          ? 'bg-white/20 text-white'
                          : 'text-white/50 hover:text-white/75',
                      )}
                    >
                      中文
                    </button>
                    <button
                      type="button"
                      onClick={() => setLanguage('en')}
                      className={cn(
                        'rounded-full px-2.5 py-1 text-xs transition-colors',
                        language === 'en'
                          ? 'bg-white/20 text-white'
                          : 'text-white/50 hover:text-white/75',
                      )}
                    >
                      EN
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={onClose}
                    className={cn(
                      'rounded-full border border-white/15 px-3 py-1.5 text-xs text-white/55',
                      'transition-colors hover:border-white/25 hover:text-white/85',
                    )}
                  >
                    {copy.back}
                  </button>
                </div>
              </div>

              {username ? (
                <div className="mb-6">
                  <InfoRow label={copy.username} value={username} />
                  <InfoRow label={copy.userId} value={userId ?? '—'} />
                  <InfoRow label={copy.sessionId} value={sessionId} />
                  <InfoRow label={copy.loginTime} value={loggedInLabel} />
                </div>
              ) : (
                <p className="mb-6 text-sm leading-relaxed text-white/50">
                  {copy.loginRequired}
                </p>
              )}

              <p className="mb-5 text-xs leading-relaxed text-white/35">
                {copy.sessionBinding}
              </p>

              {isDeveloper && (
                <div className="mb-5 flex justify-center lg:hidden">
                  <IntimacyBar
                    trust={trust}
                    editable={isAdmin}
                    saving={trustSaving}
                    deltaFlash={deltaFlash}
                    onChange={(value) => void setTrustPoints(value)}
                  />
                </div>
              )}

              <div className="flex gap-2">
                {username && onLogout && (
                  <button
                    type="button"
                    onClick={onLogout}
                    className={cn(
                      'flex-1 rounded-full border border-red-400/25 py-2.5 text-sm text-red-400/90',
                      'transition-colors hover:border-red-400/40 hover:bg-red-400/8',
                    )}
                  >
                    {copy.logout}
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className={cn(
                    'flex-1 rounded-full border border-white/20 bg-white/10 py-2.5 text-sm text-[#f5f5f5]',
                    'transition-colors hover:border-white/30 hover:bg-white/14',
                  )}
                >
                  {copy.close}
                </button>
              </div>
            </Panel>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
