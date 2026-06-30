import { cn } from '../../lib/cn'
import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'ghost' | 'soft'
}

export function Button({
  className,
  variant = 'soft',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-glow/50',
        variant === 'soft' &&
          'bg-surface text-foreground border border-border hover:bg-background',
        variant === 'ghost' && 'text-muted hover:text-foreground',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
