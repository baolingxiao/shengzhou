import { StatusOrb, type StatusOrbState } from '../system/StatusOrb'
import { cn } from '../../lib/cn'

type ConversationHeaderProps = {
  name: string
  statusLabel: string
  orbState: StatusOrbState
  onLogout?: () => void
  trailing?: React.ReactNode
  className?: string
}

/** 极简对话顶栏：角色名 + 状态光核 */
export function ConversationHeader({
  name,
  statusLabel,
  orbState,
  onLogout,
  trailing,
  className,
}: ConversationHeaderProps) {
  const showStatus = statusLabel !== 'Ready' && statusLabel !== 'Offline'

  return (
    <header
      className={cn(
        'flex shrink-0 items-center justify-between gap-3 border-b border-jarvis-border/50 pb-3.5',
        className,
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <StatusOrb state={orbState} size="sm" breathe />
        <div className="min-w-0">
          <h1 className="truncate text-[15px] font-normal tracking-[-0.02em] text-jarvis-text">
            {name}
          </h1>
          {showStatus && (
            <p className="truncate text-[11px] text-jarvis-text-soft">{statusLabel}</p>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {trailing}
        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="rounded-full border border-jarvis-border/80 px-2.5 py-1 text-[11px] text-jarvis-text-soft transition-colors hover:border-jarvis-border-strong hover:text-jarvis-text-muted"
          >
            退出
          </button>
        )}
      </div>
    </header>
  )
}
