import { motion } from 'motion/react'
import { type FormEvent, useState } from 'react'
import { cn } from '../../lib/cn'
import { UserProfileButton } from '../user/UserProfileButton'

type StartGateProps = {
  visible: boolean
  loading: boolean
  authenticated: boolean
  loggingIn?: boolean
  loginError?: string | null
  onLogin: (username: string, password: string) => Promise<void>
  onStart: () => void
  onOpenProfile?: () => void
}

const primaryButtonClass = cn(
  'rounded-full border border-white/20 bg-white/10 px-10 py-4',
  'text-lg font-medium tracking-wide text-[#f5f5f5]',
  'backdrop-blur-sm transition-all duration-300',
  'hover:border-white/35 hover:bg-white/15 hover:scale-[1.02]',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30',
  'disabled:cursor-wait disabled:opacity-40 disabled:hover:scale-100',
)

const fieldClass = cn(
  'w-full rounded-full border border-white/15 bg-white/5 px-5 py-3',
  'text-base text-[#f5f5f5] placeholder:text-white/35',
  'outline-none transition-colors focus:border-white/30 focus:bg-white/8',
)

/** Center start button on black screen — login once, then unlocks audio + animation */
export function StartGate({
  visible,
  loading,
  authenticated,
  loggingIn = false,
  loginError,
  onLogin,
  onStart,
  onOpenProfile,
}: StartGateProps) {
  const [showLoginForm, setShowLoginForm] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  if (!visible) return null

  const handleLoginSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (loggingIn || !username.trim() || !password) return
    void onLogin(username, password)
  }

  const profileButton = onOpenProfile ? (
    <UserProfileButton
      onClick={onOpenProfile}
      className="absolute left-4 top-4 z-10 md:left-6 md:top-6"
    />
  ) : null

  if (!authenticated) {
    if (!showLoginForm) {
      return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-[#050505]">
          {profileButton}
          <motion.button
            type="button"
            onClick={() => setShowLoginForm(true)}
            className={primaryButtonClass}
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          >
            登录
          </motion.button>
        </div>
      )
    }

    return (
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-[#050505] px-4">
        {profileButton}
        <motion.form
          onSubmit={handleLoginSubmit}
          className="flex w-full max-w-sm flex-col gap-4"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          <input
            type="text"
            autoComplete="username"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loggingIn}
            className={fieldClass}
          />
          <input
            type="password"
            autoComplete="current-password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loggingIn}
            className={fieldClass}
          />
          {loginError && (
            <p className="text-center text-sm text-red-400/90" role="alert">
              {loginError}
            </p>
          )}
          <button
            type="submit"
            disabled={loggingIn || !username.trim() || !password}
            className={cn(primaryButtonClass, 'mt-1')}
          >
            {loggingIn ? '登录中…' : '登录'}
          </button>
        </motion.form>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-[#050505]">
      {profileButton}
      <motion.button
        type="button"
        disabled={loading}
        onClick={onStart}
        className={primaryButtonClass}
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: loading ? 0.5 : 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        {loading ? '稍等…' : '来了，老弟！'}
      </motion.button>
    </div>
  )
}
