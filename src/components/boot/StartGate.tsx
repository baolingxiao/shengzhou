import { motion } from 'motion/react'
import { type FormEvent, useState } from 'react'
import { cn } from '../../lib/cn'
import { UserProfileButton } from '../user/UserProfileButton'

type StartGateProps = {
  visible: boolean
  loading: boolean
  authenticated: boolean
  role?: 'developer' | 'user' | null
  loggingIn?: boolean
  loginError?: string | null
  personaRequired?: boolean
  personaConfigured?: boolean
  personaLoading?: boolean
  personaSaving?: boolean
  personaError?: string | null
  onLogin: (username: string, password: string) => Promise<void>
  onSavePersona?: (
    displayName: string,
    stylePrompt: string,
    apiKeys: {
      chatgptApiKey: string
      claudeApiKey: string
      deepseekApiKey: string
      doubaoApiKey: string
    },
  ) => Promise<void>
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
  role = null,
  loggingIn = false,
  loginError,
  personaRequired = false,
  personaConfigured = true,
  personaLoading = false,
  personaSaving = false,
  personaError,
  onLogin,
  onSavePersona,
  onStart,
  onOpenProfile,
}: StartGateProps) {
  const [showLoginForm, setShowLoginForm] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [stylePrompt, setStylePrompt] = useState('')
  const [chatgptApiKey, setChatgptApiKey] = useState('')
  const [claudeApiKey, setClaudeApiKey] = useState('')
  const [deepseekApiKey, setDeepseekApiKey] = useState('')
  const [doubaoApiKey, setDoubaoApiKey] = useState('')

  if (!visible) return null

  const handleLoginSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (loggingIn || !username.trim() || !password) return
    void onLogin(username, password)
  }

  const handlePersonaSubmit = (event: FormEvent) => {
    event.preventDefault()
    const hasAnyApiKey = Boolean(
      chatgptApiKey.trim() ||
      claudeApiKey.trim() ||
      deepseekApiKey.trim() ||
      doubaoApiKey.trim(),
    )
    if (personaSaving || !displayName.trim() || !stylePrompt.trim() || !hasAnyApiKey) return
    void onSavePersona?.(displayName, stylePrompt, {
      chatgptApiKey,
      claudeApiKey,
      deepseekApiKey,
      doubaoApiKey,
    })
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
          <p className="text-center text-xs text-white/35">
            普通用户默认账号：user_mason / JarvisUser#2026!
          </p>
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

  if (authenticated && personaRequired && !personaConfigured) {
    const hasAnyApiKey = Boolean(
      chatgptApiKey.trim() ||
      claudeApiKey.trim() ||
      deepseekApiKey.trim() ||
      doubaoApiKey.trim(),
    )
    return (
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-[#050505] px-4">
        {profileButton}
        <motion.form
          onSubmit={handlePersonaSubmit}
          className="flex w-full max-w-xl flex-col gap-4"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          <h2 className="text-center text-lg font-medium text-[#f5f5f5]">创建你的 AI 人物</h2>
          <p className="text-center text-sm text-white/55">
            普通账户首次登录后需完成角色设置，聊天风格只按你的自定义 prompt 执行。
          </p>
          <input
            type="text"
            placeholder="角色名字（例如：墨白）"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            disabled={personaSaving || personaLoading}
            className={fieldClass}
          />
          <textarea
            placeholder="回复风格 prompt（例如：语气温和，结论优先，必要时给清晰步骤）"
            value={stylePrompt}
            onChange={(e) => setStylePrompt(e.target.value)}
            disabled={personaSaving || personaLoading}
            className={cn(
              'w-full min-h-[170px] rounded-3xl border border-white/15 bg-white/5 px-5 py-4',
              'text-sm text-[#f5f5f5] placeholder:text-white/35',
              'outline-none transition-colors focus:border-white/30 focus:bg-white/8',
            )}
          />
          <p className="text-center text-xs text-white/45">
            填写 AI API Key（四选一，至少填一个）
          </p>
          <input
            type="password"
            autoComplete="off"
            placeholder="ChatGPT API Key"
            value={chatgptApiKey}
            onChange={(e) => setChatgptApiKey(e.target.value)}
            disabled={personaSaving || personaLoading}
            className={fieldClass}
          />
          <input
            type="password"
            autoComplete="off"
            placeholder="Claude API Key"
            value={claudeApiKey}
            onChange={(e) => setClaudeApiKey(e.target.value)}
            disabled={personaSaving || personaLoading}
            className={fieldClass}
          />
          <input
            type="password"
            autoComplete="off"
            placeholder="DeepSeek API Key"
            value={deepseekApiKey}
            onChange={(e) => setDeepseekApiKey(e.target.value)}
            disabled={personaSaving || personaLoading}
            className={fieldClass}
          />
          <input
            type="password"
            autoComplete="off"
            placeholder="豆包 API Key"
            value={doubaoApiKey}
            onChange={(e) => setDoubaoApiKey(e.target.value)}
            disabled={personaSaving || personaLoading}
            className={fieldClass}
          />
          {!hasAnyApiKey && (
            <p className="text-center text-xs text-yellow-300/80">
              需至少填写一个 API Key 才能继续。
            </p>
          )}
          {personaError && (
            <p className="text-center text-sm text-red-400/90" role="alert">
              {personaError}
            </p>
          )}
          <button
            type="submit"
            disabled={
              personaSaving ||
              personaLoading ||
              !displayName.trim() ||
              !stylePrompt.trim() ||
              !hasAnyApiKey
            }
            className={cn(primaryButtonClass, 'mt-1')}
          >
            {personaSaving ? '保存中…' : '保存人物并继续'}
          </button>
          {role === 'user' && (
            <p className="text-center text-xs text-white/35">
              电脑控制模块仍可使用；沈昼开发者专属提示词不会对普通账户生效。
            </p>
          )}
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
