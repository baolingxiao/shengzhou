import { motion } from 'motion/react'
import { CheckCircle2, ExternalLink, Loader2, Monitor, MousePointer2, ShieldAlert, Sparkles, XCircle } from 'lucide-react'
import { SystemModal } from './SystemModal'
import { cn } from '../../lib/cn'
import type { PermissionsSnapshot } from '../../lib/systemApi'
import type { RecheckFeedback } from '../../hooks/useMacPermissions'

type MacPermissionsModalProps = {
  open: boolean
  snapshot: PermissionsSnapshot | null
  rechecking: boolean
  autoSettingUp: boolean
  recheckFeedback: RecheckFeedback
  showSuccessCelebration: boolean
  onAutoSetup: () => void
  onDismiss: () => void
}

function StatusBanner({
  feedback,
  busy,
  showSuccess,
}: {
  feedback: RecheckFeedback
  busy: boolean
  showSuccess: boolean
}) {
  if (showSuccess || feedback.status === 'success') {
    return (
      <motion.div
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start gap-3 rounded-2xl border border-emerald-400/50 bg-emerald-500/20 px-4 py-3 text-emerald-50"
      >
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
        <div>
          <p className="font-medium">好了，沈昼可以代你操作电脑了</p>
          <p className="mt-0.5 text-xs text-emerald-100/90">
            {feedback.status === 'success' ? feedback.message : '窗口即将关闭…'}
          </p>
        </div>
      </motion.div>
    )
  }

  if (busy || feedback.status === 'checking' || feedback.status === 'requesting') {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-sky-400/45 bg-sky-500/20 px-4 py-3 text-sky-50">
        <Loader2 className="h-5 w-5 shrink-0 animate-spin" aria-hidden />
        <div>
          <p className="font-medium">
            {feedback.status === 'requesting' ? '正在唤起系统授权…' : '正在检测…'}
          </p>
          <p className="mt-0.5 text-xs text-sky-100/85">
            {feedback.status === 'requesting'
              ? feedback.message
              : '请稍候，沈昼在确认你是否已在系统里点「允许」'}
          </p>
        </div>
      </div>
    )
  }

  if (feedback.status === 'partial') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex items-start gap-3 rounded-2xl border border-amber-400/55 bg-amber-500/25 px-4 py-3 text-amber-50"
      >
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
        <div>
          <p className="font-medium">还差一步</p>
          <p className="mt-1 text-xs leading-relaxed">{feedback.message}</p>
          {'at' in feedback && (
            <p className="mt-1 text-[10px] text-amber-100/70">上次检测 {feedback.at}</p>
          )}
        </div>
      </motion.div>
    )
  }

  if (feedback.status === 'error') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex items-start gap-3 rounded-2xl border border-red-400/50 bg-red-500/20 px-4 py-3 text-red-50"
      >
        <XCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
        <div>
          <p className="font-medium">出了点问题</p>
          <p className="mt-1 text-xs leading-relaxed">{feedback.message}</p>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="rounded-2xl border border-violet-400/35 bg-violet-500/15 px-4 py-3 text-violet-50">
      <p className="text-sm leading-relaxed">
        沈昼需要你的允许才能帮你操作电脑。点下面按钮，按<strong className="text-white">系统弹窗</strong>
        提示点「允许」即可，不用自己找 Python。
      </p>
    </div>
  )
}

export function MacPermissionsModal({
  open,
  snapshot,
  rechecking,
  autoSettingUp,
  recheckFeedback,
  showSuccessCelebration,
  onAutoSetup,
  onDismiss,
}: MacPermissionsModalProps) {
  if (!snapshot) return null

  const busy = rechecking || autoSettingUp
  const inApp = snapshot.running_in_app !== false
  const appName = snapshot.tcc_identity || snapshot.bundle_name || '贾维斯'
  const needsAppLaunch = !inApp && !snapshot.allow_terminal_agent

  const items = [
    { key: 'accessibility', icon: MousePointer2, ...snapshot.accessibility },
    { key: 'screen_recording', icon: Monitor, ...snapshot.screen_recording },
  ]

  const highlightMissing =
    recheckFeedback.status === 'partial' ? recheckFeedback.missing : []

  return (
    <SystemModal open={open} title={needsAppLaunch ? '请用「贾维斯」App 启动' : '允许沈昼使用你的电脑'} className="max-w-lg">
      <StatusBanner feedback={recheckFeedback} busy={busy} showSuccess={showSuccessCelebration} />

      {needsAppLaunch ? (
        <div className="space-y-3 rounded-2xl border border-amber-400/45 bg-amber-500/15 px-4 py-3 text-amber-50">
          <p className="text-sm leading-relaxed">
            当前是从 <strong className="text-white">Terminal / Python</strong> 启动的，系统设置里只会出现
            Terminal 或 Python，<strong className="text-white">无法直接授权「贾维斯」</strong>。
          </p>
          <p className="text-sm leading-relaxed text-amber-100/90">
            请关闭当前启动方式，改用打包好的 App：
          </p>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-amber-100/95">
            <li>在项目目录运行 <code className="rounded bg-black/30 px-1">./scripts/macos/make_jarvis_app.sh</code></li>
            <li>双击 <code className="rounded bg-black/30 px-1">dist/贾维斯.app</code> 打开</li>
            <li>在系统设置 → 隐私与安全性 中打开「贾维斯」</li>
          </ol>
        </div>
      ) : snapshot.needs_app_restart ? (
        <div className="space-y-2 rounded-2xl border border-sky-400/45 bg-sky-500/15 px-4 py-3 text-sky-50">
          <p className="text-sm leading-relaxed">
            屏幕录制已就绪，但<strong className="text-white">辅助功能需要重启 App</strong> 才会生效。
          </p>
          <p className="text-sm leading-relaxed text-sky-100/90">
            若系统设置里已打开「{appName}」，请按 <strong className="text-white">⌘Q</strong>{' '}
            完全退出贾维斯，再重新双击打开（不要只关窗口）。
          </p>
        </div>
      ) : (
        <p className="text-center text-sm text-white/75">
          只需在 macOS 弹窗里点<strong className="text-white"> 允许 </strong>
          ，或在系统设置里打开「{appName}」开关。贾维斯会自动完成检测。
        </p>
      )}

      <ul className="space-y-2">
        {items.map((item) => {
          const Icon = item.icon
          const granted = item.granted
          const missing = highlightMissing.includes(item.label ?? '')
          return (
            <li
              key={item.key}
              className={cn(
                'flex items-center gap-3 rounded-xl border px-3 py-2.5 transition',
                granted
                  ? 'border-emerald-400/40 bg-emerald-500/10'
                  : missing
                    ? 'border-amber-400/60 bg-amber-500/15 ring-1 ring-amber-400/30'
                    : 'border-white/15 bg-black/20',
              )}
            >
              <Icon className={cn('h-4 w-4 shrink-0', granted ? 'text-emerald-300' : 'text-amber-200')} />
              <span className="flex-1 text-sm text-white/90">{item.label}</span>
              <span
                className={cn(
                  'text-xs font-medium',
                  granted ? 'text-emerald-300' : 'text-amber-200',
                )}
              >
                {granted ? '✓' : '待允许'}
              </span>
            </li>
          )
        })}
      </ul>

      <button
        type="button"
        disabled={busy || showSuccessCelebration || needsAppLaunch}
        onClick={onAutoSetup}
        className={cn(
          'flex w-full items-center justify-center gap-2 rounded-2xl py-4 text-base font-semibold shadow-lg transition',
          busy || needsAppLaunch
            ? 'cursor-not-allowed bg-white/20 text-white/60'
            : 'bg-white text-[#1a1520] hover:bg-white/95 active:scale-[0.99]',
        )}
      >
        {needsAppLaunch ? (
          <>
            <ExternalLink className="h-5 w-5" />
            请先用 贾维斯.app 启动
          </>
        ) : busy ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            处理中…
          </>
        ) : (
          <>
            <Sparkles className="h-5 w-5" />
            一键授权
          </>
        )}
      </button>

      <button
        type="button"
        disabled={busy}
        onClick={onDismiss}
        className="w-full py-2 text-sm text-white/55 hover:text-white/80 disabled:opacity-50"
      >
        稍后再说
      </button>

      <details className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs text-white/50">
        <summary className="cursor-pointer select-none text-white/65">高级 / 技术人员</summary>
        <p className="mt-2 leading-relaxed">
          运行身份：{inApp ? '贾维斯.app' : 'Terminal / Python（开发模式）'}
          <br />
          后端进程：{snapshot.backend_process_path}
          <br />
          {needsAppLaunch
            ? '开发调试可在 .env 设置 NEURALPAL_ALLOW_TERMINAL_AGENT=true，但正式使用请用 贾维斯.app。'
            : '若系统未弹出提示，可在辅助功能与屏幕录制中用 + 添加上述路径。'}
        </p>
      </details>
    </SystemModal>
  )
}
