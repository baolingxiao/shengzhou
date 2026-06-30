import { CheckCircle2, ExternalLink, Loader2, Monitor, MousePointer2, RefreshCw, XCircle } from 'lucide-react'
import { SystemModal } from './SystemModal'
import { useMacPermissionsContext } from '../../contexts/MacPermissionsContext'
import { cn } from '../../lib/cn'

export function MacPermissionsStatusPanel() {
  const {
    statusPanelOpen,
    closeStatusPanel,
    snapshot,
    rechecking,
    autoSettingUp,
    recheckAfterSettings,
    runAutoSetup,
    openSettings,
  } = useMacPermissionsContext()

  if (!snapshot) return null

  const busy = rechecking || autoSettingUp
  const appName = snapshot.tcc_identity || snapshot.bundle_name || '贾维斯'
  const inApp = snapshot.running_in_app !== false

  const items = [
    { key: 'accessibility', icon: MousePointer2, ...snapshot.accessibility },
    { key: 'screen_recording', icon: Monitor, ...snapshot.screen_recording },
  ]

  return (
    <SystemModal open={statusPanelOpen} title="贾维斯 · 系统权限" className="max-w-lg">
      <p className="text-sm leading-relaxed text-white/75">
        以下为 macOS 授予<strong className="text-white">「{appName}」</strong>的权限状态。
        {snapshot.all_granted
          ? ' 沈昼可以代你操作本机。'
          : ' 未就绪时代操功能不可用。'}
      </p>

      <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-2 text-xs text-white/55">
        <p>运行身份：{inApp ? '贾维斯.app' : 'Terminal / Python（开发模式）'}</p>
        {snapshot.app_bundle_path && (
          <p className="mt-1 truncate" title={snapshot.app_bundle_path}>
            App 路径：{snapshot.app_bundle_path}
          </p>
        )}
        <p className="mt-1 truncate" title={snapshot.backend_process_path}>
          进程镜像：{snapshot.backend_process_name ?? '—'}
        </p>
        {snapshot.checked_at && (
          <p className="mt-1">检测时间：{new Date(snapshot.checked_at).toLocaleString('zh-CN')}</p>
        )}
      </div>

      <ul className="space-y-2">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <li
              key={item.key}
              className={cn(
                'flex items-start gap-3 rounded-xl border px-3 py-2.5',
                item.granted
                  ? 'border-emerald-400/40 bg-emerald-500/10'
                  : 'border-amber-400/40 bg-amber-500/10',
              )}
            >
              <Icon
                className={cn('mt-0.5 h-4 w-4 shrink-0', item.granted ? 'text-emerald-300' : 'text-amber-200')}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm text-white/90">{item.label}</span>
                  <span
                    className={cn(
                      'text-xs font-medium',
                      item.granted ? 'text-emerald-300' : 'text-amber-200',
                    )}
                  >
                    {item.granted ? '已授权' : '未授权'}
                  </span>
                </div>
                {item.detail && (
                  <p className="mt-1 text-xs leading-relaxed text-white/50">{item.detail}</p>
                )}
                {'probe' in item && item.probe && (
                  <p className="mt-1 text-[11px] leading-relaxed text-white/40">{item.probe}</p>
                )}
              </div>
            </li>
          )
        })}
      </ul>

      {snapshot.tcc_cdhash_mismatch_suspected && snapshot.code_signing?.detail ? (
        <div className="rounded-xl border border-rose-400/40 bg-rose-500/15 px-3 py-2 text-sm text-rose-100">
          {snapshot.code_signing.detail}
        </div>
      ) : snapshot.all_granted ? (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-400/40 bg-emerald-500/15 px-3 py-2 text-sm text-emerald-100">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          本机代操已就绪
        </div>
      ) : snapshot.needs_app_restart ? (
        <div className="rounded-xl border border-sky-400/40 bg-sky-500/15 px-3 py-2 text-sm text-sky-100">
          系统设置里若已打开辅助功能，请按 <strong>⌘Q</strong> 完全退出贾维斯后重新打开。
        </div>
      ) : (
        <div className="flex items-start gap-2 rounded-xl border border-amber-400/40 bg-amber-500/15 px-3 py-2 text-sm text-amber-100">
          <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{snapshot.message}</span>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void recheckAfterSettings()}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/25 px-3 py-1.5 text-xs text-white/85 transition hover:border-white/40 disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          重新检测
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void openSettings('accessibility')}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/25 px-3 py-1.5 text-xs text-white/85 transition hover:border-white/40 disabled:opacity-50"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          辅助功能设置
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void openSettings('screen_recording')}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/25 px-3 py-1.5 text-xs text-white/85 transition hover:border-white/40 disabled:opacity-50"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          屏幕录制设置
        </button>
      </div>

      {!snapshot.all_granted && inApp && (
        <button
          type="button"
          disabled={busy || snapshot.needs_app_restart}
          onClick={() => void runAutoSetup()}
          className="w-full rounded-2xl bg-white/90 py-3 text-sm font-medium text-[#1a1520] transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? '处理中…' : '一键授权（唤起系统弹窗）'}
        </button>
      )}

      <button
        type="button"
        onClick={closeStatusPanel}
        className="w-full py-2 text-sm text-white/55 hover:text-white/80"
      >
        关闭
      </button>
    </SystemModal>
  )
}
