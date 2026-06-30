import { cn } from '../../lib/cn'
import type { WorkModeSnapshot } from '../../lib/workModeApi'

type WorkModeBadgeProps = {
  snapshot: WorkModeSnapshot | null
  className?: string
}

const MODE_STYLE: Record<
  WorkModeSnapshot['mode'],
  { label: string; className: string }
> = {
  work: {
    label: '上班中',
    className: 'border-sky-300/40 bg-sky-400/20 text-sky-100',
  },
  companion: {
    label: '陪伴中',
    className: 'border-violet-300/35 bg-violet-400/15 text-violet-100',
  },
  overtime: {
    label: '加班中',
    className: 'border-amber-300/45 bg-amber-400/20 text-amber-100',
  },
}

export function WorkModeBadge({ snapshot, className }: WorkModeBadgeProps) {
  if (!snapshot) return null
  const style = MODE_STYLE[snapshot.mode]
  return (
    <div className={cn('flex flex-col items-end gap-1', className)}>
      <span
        className={cn(
          'rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide backdrop-blur-sm',
          style.className,
        )}
      >
        {snapshot.mode_label || style.label}
      </span>
      <span className="text-[10px] text-white/55 tabular-nums">
        {snapshot.clock} · {snapshot.work_window}
      </span>
      {snapshot.awaiting_overtime_consent && (
        <span className="max-w-[9rem] text-right text-[10px] leading-snug text-amber-200/90">
          待你批准加班
        </span>
      )}
    </div>
  )
}
