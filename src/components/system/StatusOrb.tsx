import { motion } from 'motion/react'
import { cn } from '../../lib/cn'

export type StatusOrbState = 'ready' | 'thinking' | 'listening' | 'offline' | 'speaking'

type StatusOrbProps = {
  state: StatusOrbState
  className?: string
  size?: 'sm' | 'md'
  /** 名字旁轻微呼吸 */
  breathe?: boolean
}

const stateColors: Record<StatusOrbState, string> = {
  ready: 'from-[rgba(245,242,234,0.95)] to-[rgba(245,215,161,0.55)]',
  thinking: 'from-[rgba(230,220,205,0.9)] to-[rgba(200,190,175,0.45)]',
  listening: 'from-[rgba(245,238,222,0.92)] to-[rgba(216,199,170,0.5)]',
  speaking: 'from-[rgba(255,248,236,0.95)] to-[rgba(245,215,161,0.6)]',
  offline: 'from-[rgba(180,170,165,0.5)] to-[rgba(120,115,110,0.25)]',
}

const stateGlow: Record<StatusOrbState, string> = {
  ready: 'rgba(245,238,222,0.22)',
  thinking: 'rgba(216,199,170,0.2)',
  listening: 'rgba(245,215,161,0.28)',
  speaking: 'rgba(245,238,222,0.3)',
  offline: 'rgba(120,115,110,0.15)',
}

/** Apple 风格状态呼吸光核 — 暖白 / 香槟 */
export function StatusOrb({ state, className, size = 'md', breathe }: StatusOrbProps) {
  const dim = size === 'sm' ? 'h-2 w-2' : 'h-2.5 w-2.5'
  const wrap = size === 'sm' ? 'h-6 w-6' : 'h-8 w-8'
  const active = state === 'thinking' || state === 'listening' || state === 'speaking'

  return (
    <div className={cn('relative flex items-center justify-center', wrap, className)} aria-hidden>
      <motion.span
        className="absolute inset-0 rounded-full blur-md"
        style={{ backgroundColor: stateGlow[state] }}
        animate={
          active || breathe
            ? { scale: [0.88, 1.12, 0.88], opacity: [0.35, 0.62, 0.35] }
            : { scale: [0.92, 1.04, 0.92], opacity: [0.28, 0.45, 0.28] }
        }
        transition={{
          duration: active ? 2.2 : 4.2,
          repeat: Infinity,
          ease: [0.22, 1, 0.36, 1],
        }}
      />
      <span
        className={cn(
          'relative rounded-full bg-gradient-to-b',
          dim,
          stateColors[state],
        )}
        style={{ boxShadow: `0 0 8px ${stateGlow[state]}` }}
      />
    </div>
  )
}
