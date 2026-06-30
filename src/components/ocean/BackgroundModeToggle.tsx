import { cn } from '../../lib/cn'
import type { BackgroundMode } from '../../hooks/useBackgroundMode'

type BackgroundModeToggleProps = {
  mode: BackgroundMode
  onToggle: () => void
  className?: string
}

function OceanIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M3 14c2.5-2 5-2 7.5 0s5 2 7.5 0 3-2 3-2"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M3 10c2-1.5 4.5-1.5 6.5 0s4.5 1.5 6.5 0 2.5-1 4-1"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.55"
      />
    </svg>
  )
}

function SolidIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth="1.5" opacity="0.45" />
      <circle cx="12" cy="12" r="3.5" fill="currentColor" opacity="0.85" />
    </svg>
  )
}

export function BackgroundModeToggle({ mode, onToggle, className }: BackgroundModeToggleProps) {
  const isOcean = mode === 'ocean'

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={isOcean ? '切换为纯色背景' : '切换为海洋背景'}
      title={isOcean ? '纯色背景' : '海洋背景'}
      className={cn(
        'flex h-9 w-9 items-center justify-center rounded-full',
        'border border-white/20 bg-[rgba(55,82,92,0.32)] text-white/80',
        'shadow-[0_4px_24px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.14)]',
        'backdrop-blur-xl backdrop-saturate-150',
        'transition-[background-color,box-shadow,transform,color] duration-300 ease-out',
        'hover:border-white/28 hover:bg-[rgba(70,106,119,0.42)] hover:text-white',
        'active:scale-95',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/25',
        className,
      )}
    >
      {isOcean ? <SolidIcon className="h-[18px] w-[18px]" /> : <OceanIcon className="h-[18px] w-[18px]" />}
    </button>
  )
}
