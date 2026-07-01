import { cn } from '../../lib/cn'

type SolidBackgroundProps = {
  active: boolean
  className?: string
}

/**
 * 非海洋模式时保持氛围层可见。
 * 实际渐变由 CinematicAtmosphere 提供，此处仅作模式切换时的透明度过渡占位。
 */
export function SolidBackground({ active, className }: SolidBackgroundProps) {
  return (
    <div
      className={cn(
        'pointer-events-none absolute inset-0 z-[1] transition-opacity duration-1000 ease-out',
        active ? 'opacity-100' : 'opacity-0',
        className,
      )}
      aria-hidden
    />
  )
}
