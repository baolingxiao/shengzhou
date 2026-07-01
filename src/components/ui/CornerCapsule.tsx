import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

type CornerCapsuleProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: ReactNode
  label?: string
  /** 记忆入口等核心能力轻微香槟强调 */
  accent?: boolean
  /** 右上角状态点 */
  statusDot?: 'ok' | 'warn' | 'alert'
}

/** 四角统一半透明胶囊入口 */
export function CornerCapsule({
  icon,
  label,
  accent,
  statusDot,
  className,
  ...props
}: CornerCapsuleProps) {
  return (
    <button
      type="button"
      className={cn(
        'flex items-center gap-2 rounded-full border backdrop-blur-xl',
        'border-white/[0.12] bg-[rgba(18,20,28,0.48)] text-[rgba(245,242,234,0.62)]',
        'shadow-[0_8px_32px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.06)]',
        'transition-[background-color,border-color,color,box-shadow,transform] duration-300 ease-out',
        'hover:border-white/[0.2] hover:bg-[rgba(28,30,36,0.62)] hover:text-[rgba(245,242,234,0.88)]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(245,215,161,0.25)]',
        'active:scale-[0.98]',
        accent &&
          'border-[rgba(245,215,161,0.22)] text-[rgba(245,238,222,0.78)] hover:border-[rgba(245,215,161,0.38)] hover:shadow-[0_8px_36px_rgba(245,215,161,0.08)]',
        label ? 'h-10 px-3.5 text-xs font-medium' : 'h-9 w-9 justify-center',
        className,
      )}
      {...props}
    >
      {icon && (
        <span className={cn('relative shrink-0 opacity-85', !label && 'text-base')} aria-hidden>
          {icon}
          {statusDot && (
            <span
              className={cn(
                'absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full ring-1 ring-[rgba(11,13,18,0.8)]',
                statusDot === 'ok' && 'bg-emerald-400/90',
                statusDot === 'warn' && 'bg-amber-400/90',
                statusDot === 'alert' && 'bg-red-400/85',
              )}
            />
          )}
        </span>
      )}
      {label && <span>{label}</span>}
    </button>
  )
}
