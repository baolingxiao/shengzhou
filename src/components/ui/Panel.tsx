import { cn } from '../../lib/cn'
import type { HTMLAttributes } from 'react'

type PanelProps = HTMLAttributes<HTMLDivElement> & {
  glow?: boolean
  /** 上浅下深渐变玻璃面板 */
  gradient?: boolean
}

export function Panel({ className, glow = false, gradient = false, children, ...props }: PanelProps) {
  return (
    <div
      className={cn(
        'rounded-3xl border backdrop-blur-xl',
        gradient
          ? 'border-white/20 bg-[linear-gradient(180deg,rgba(243,237,228,0.08)_0%,rgba(243,237,228,0.38)_28%,rgba(243,237,228,0.72)_58%,rgba(243,237,228,0.94)_100%)] shadow-[0_12px_48px_-16px_rgba(0,0,0,0.28)]'
          : 'border-border bg-surface/80 backdrop-blur-sm',
        glow && 'shadow-[0_0_60px_-12px_rgba(0,90,167,0.22)]',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}
