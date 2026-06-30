import { motion, AnimatePresence } from 'motion/react'
import { cn } from '../../lib/cn'
import { useUserSession } from '../../contexts/UserSessionContext'
import { Panel } from '../ui/Panel'

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
  const { username, userId, sessionId, loggedInAt } = useUserSession()

  const loggedInLabel =
    loggedInAt != null
      ? new Date(loggedInAt).toLocaleString('zh-CN', {
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
                    <h1 className="text-lg font-medium tracking-tight text-[#f5f5f5]">用户信息</h1>
                    <p className="mt-0.5 text-sm text-white/45">
                      {username ? '已登录' : '未登录'}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className={cn(
                    'rounded-full border border-white/15 px-3 py-1.5 text-xs text-white/55',
                    'transition-colors hover:border-white/25 hover:text-white/85',
                  )}
                >
                  返回
                </button>
              </div>

              {username ? (
                <div className="mb-6">
                  <InfoRow label="用户名" value={username} />
                  <InfoRow label="用户 ID" value={userId ?? '—'} />
                  <InfoRow label="记忆会话 ID" value={sessionId} />
                  <InfoRow label="登录时间" value={loggedInLabel} />
                </div>
              ) : (
                <p className="mb-6 text-sm leading-relaxed text-white/50">
                  请先登录。不同用户 ID 拥有独立的 AI 对话记忆，互不影响。
                </p>
              )}

              <p className="mb-5 text-xs leading-relaxed text-white/35">
                记忆会话 ID 与当前用户绑定。切换账号后，沈昼将读取该用户专属的对话历史与短期记忆。
              </p>

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
                    退出登录
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
                  关闭
                </button>
              </div>
            </Panel>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
