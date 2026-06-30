import { cn } from '../../lib/cn'

type SolidBackgroundProps = {
  active: boolean
  className?: string
}

/** 初始纯色径向渐变背景 */
export function SolidBackground({ active, className }: SolidBackgroundProps) {
  return (
    <div
      className={cn(
        'pointer-events-none absolute inset-0 z-0 transition-opacity duration-700 ease-out',
        active ? 'opacity-100' : 'opacity-0',
        className,
      )}
      style={{
        backgroundColor: '#0f0f14',
        backgroundImage: `radial-gradient(
          circle at center,
          #466a77 0%,
          #3e5965 25%,
          #2f4952 55%,
          #1b2a30 80%,
          #0f0f14 100%
        )`,
      }}
      aria-hidden
    />
  )
}
