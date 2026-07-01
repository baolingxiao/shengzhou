import { cn } from '../../lib/cn'
import type { HTMLAttributes } from 'react'

type PanelProps = HTMLAttributes<HTMLDivElement> & {
  glow?: boolean
  /** 上浅下深渐变玻璃面板 */
  gradient?: boolean
  /** Jarvis 暗色玻璃（主聊天推荐） */
  jarvis?: boolean
}

export function Panel({
  className,
  glow = false,
  gradient = false,
  jarvis = false,
  children,
  ...props
}: PanelProps) {
  return (
    <div
      className={cn(
        'rounded-jarvis-xl border backdrop-blur-[var(--blur-jarvis)]',
        jarvis &&
          'border-jarvis-border bg-jarvis-surface-dark text-jarvis-text shadow-[0_30px_100px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)]',
        !jarvis &&
          gradient &&
          'border-white/20 bg-[linear-gradient(180deg,rgba(243,237,228,0.08)_0%,rgba(243,237,228,0.38)_28%,rgba(243,237,228,0.72)_58%,rgba(243,237,228,0.94)_100%)] shadow-[0_12px_48px_-16px_rgba(0,0,0,0.28)]',
        !jarvis && !gradient && 'border-border bg-surface/80 backdrop-blur-sm',
        glow &&
          (jarvis
            ? 'shadow-[0_30px_100px_rgba(0,0,0,0.35),0_0_60px_-12px_rgba(245,238,222,0.08),inset_0_1px_0_rgba(255,255,255,0.08)]'
            : 'shadow-[0_0_60px_-12px_rgba(216,199,170,0.18)]'),
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}
