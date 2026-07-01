import { cn } from '../../lib/cn'
import type { BackgroundMode } from '../../hooks/useBackgroundMode'
import { CornerCapsule } from '../ui/CornerCapsule'

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
    <CornerCapsule
      onClick={onToggle}
      aria-label={isOcean ? '切换为纯色背景' : '切换为海洋背景'}
      title={isOcean ? '纯色背景' : '海洋背景'}
      icon={isOcean ? <SolidIcon className="h-[18px] w-[18px]" /> : <OceanIcon className="h-[18px] w-[18px]" />}
      className={cn(className)}
    />
  )
}
