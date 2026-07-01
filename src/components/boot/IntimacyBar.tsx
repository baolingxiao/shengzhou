import {
  type KeyboardEvent,
  type PointerEvent,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { cn } from '../../lib/cn'
import type { TrustSnapshot } from '../../lib/trustApi'

type IntimacyBarProps = {
  trust: TrustSnapshot | null
  editable: boolean
  saving?: boolean
  deltaFlash?: number | null
  onChange?: (value: number) => void
  className?: string
}

type OrbPalette = {
  core: string
  glow: string
  rim: string
  rail: string
}

function orbPalette(tp: number): OrbPalette {
  if (tp <= 30) {
    return {
      core: 'rgba(232, 240, 255, 0.92)',
      glow: 'rgba(140, 175, 230, 0.28)',
      rim: 'rgba(190, 210, 245, 0.55)',
      rail: 'rgba(160, 190, 230, 0.22)',
    }
  }
  if (tp <= 70) {
    return {
      core: 'rgba(236, 238, 242, 0.94)',
      glow: 'rgba(195, 200, 210, 0.26)',
      rim: 'rgba(215, 220, 228, 0.5)',
      rail: 'rgba(200, 205, 215, 0.2)',
    }
  }
  const warmth = Math.min(1, (tp - 71) / 29)
  const atMax = tp >= 100
  const glowAlpha = atMax ? 0.22 : 0.18 + warmth * 0.14
  return {
    core: atMax ? 'rgba(255, 248, 236, 0.9)' : `rgba(255, ${238 + warmth * 10}, ${215 + warmth * 12}, 0.9)`,
    glow: `rgba(245, 220, 175, ${glowAlpha})`,
    rim: `rgba(255, 235, 205, ${atMax ? 0.38 : 0.32 + warmth * 0.18})`,
    rail: `rgba(230, 210, 175, ${atMax ? 0.18 : 0.14 + warmth * 0.1})`,
  }
}

export function IntimacyBar({
  trust,
  editable,
  saving = false,
  deltaFlash = null,
  onChange,
  className,
}: IntimacyBarProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const draggingRef = useRef(false)
  const tooltipId = useId()
  const [dragValue, setDragValue] = useState<number | null>(null)
  const [hovered, setHovered] = useState(false)
  const [focused, setFocused] = useState(false)

  const min = trust?.min ?? 0
  const max = trust?.max ?? 100
  const committed = trust?.trust_points ?? min
  const value = dragValue ?? committed
  const span = Math.max(1, max - min)
  const percent = ((value - min) / span) * 100
  const palette = orbPalette(value)
  const levelName = trust?.level_name?.trim() || '关系建立中'
  const editing = dragValue !== null
  const showValue = hovered || focused || editing
  const showTooltip = hovered || focused || editing
  const showDelta = deltaFlash != null && deltaFlash !== 0

  useEffect(() => {
    if (!draggingRef.current) setDragValue(null)
  }, [committed])

  const clamp = useCallback(
    (n: number) => Math.round(Math.max(min, Math.min(max, n))),
    [min, max],
  )

  const valueFromClientY = useCallback(
    (clientY: number) => {
      const track = trackRef.current
      if (!track) return value
      const rect = track.getBoundingClientRect()
      const ratio = 1 - (clientY - rect.top) / rect.height
      return clamp(min + ratio * span)
    },
    [clamp, min, span, value],
  )

  const commitValue = useCallback(
    (next: number) => {
      if (!editable || !onChange) return
      onChange(clamp(next))
    },
    [clamp, editable, onChange],
  )

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (!editable || !onChange) return
    event.preventDefault()
    draggingRef.current = true
    event.currentTarget.setPointerCapture(event.pointerId)
    setDragValue(valueFromClientY(event.clientY))
  }

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!editable || !draggingRef.current) return
    event.preventDefault()
    setDragValue(valueFromClientY(event.clientY))
  }

  const finishDrag = (event: PointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current) return
    draggingRef.current = false
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    commitValue(valueFromClientY(event.clientY))
    setDragValue(null)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!editable || !onChange) return
    let next: number | null = null
    if (event.key === 'ArrowUp' || event.key === 'ArrowRight') next = value + 1
    if (event.key === 'ArrowDown' || event.key === 'ArrowLeft') next = value - 1
    if (event.key === 'Home') next = min
    if (event.key === 'End') next = max
    if (next == null) return
    event.preventDefault()
    commitValue(next)
  }

  return (
    <div
      className={cn(
        'group relative flex w-[3.15rem] shrink-0 flex-col items-center gap-2.5',
        'rounded-[1.35rem] border border-white/[0.1] bg-[rgba(16,18,24,0.5)]',
        'px-2 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_16px_48px_rgba(0,0,0,0.28)] backdrop-blur-2xl',
        saving && 'opacity-70',
        className,
      )}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <span className="pointer-events-none text-[9px] font-medium tracking-[0.16em] text-white/48">
        关系
      </span>

      <div
        ref={trackRef}
        tabIndex={editable ? 0 : -1}
        className={cn(
          'relative flex min-h-[148px] w-full flex-1 items-stretch justify-center outline-none',
          editable ? 'cursor-ns-resize touch-none focus-visible:ring-1 focus-visible:ring-white/25' : 'cursor-default',
        )}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishDrag}
        onPointerCancel={finishDrag}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={handleKeyDown}
        role={editable ? 'slider' : 'progressbar'}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-readonly={!editable}
        aria-label={`关系亲密度，当前 ${value}，${levelName}`}
        aria-describedby={showTooltip ? tooltipId : undefined}
      >
        {showDelta && (
          <motion.span
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={cn(
              'pointer-events-none absolute -top-1 left-1/2 z-20 -translate-x-1/2 text-[10px] font-medium tabular-nums',
              deltaFlash! < 0 ? 'text-rose-300/90' : 'text-emerald-200/90',
            )}
          >
            {deltaFlash! > 0 ? `+${deltaFlash}` : deltaFlash}
          </motion.span>
        )}

        <div className="pointer-events-none relative h-full w-1 rounded-full bg-white/[0.06]">
          <div
            className="absolute inset-x-0 bottom-0 rounded-full transition-[height] duration-300 ease-out"
            style={{
              height: `${percent}%`,
              background: `linear-gradient(to top, ${palette.rail}, transparent)`,
            }}
          />
        </div>

        <motion.div
          className="pointer-events-none absolute left-1/2 z-10 -translate-x-1/2"
          style={{ bottom: `calc(${percent}% - 10px)` }}
          animate={{
            scale: editing ? 1.08 : [1, 1.035, 1],
            opacity: editing ? 1 : [0.88, 1, 0.88],
          }}
          transition={
            editing
              ? { type: 'spring', damping: 26, stiffness: 340 }
              : { duration: 4.8, repeat: Infinity, ease: 'easeInOut' }
          }
        >
          <div
            className="relative h-5 w-5 rounded-full"
            style={{
              background: `radial-gradient(circle at 38% 32%, ${palette.core} 0%, rgba(24,26,34,0.15) 68%, transparent 100%)`,
              boxShadow: `0 0 14px ${palette.glow}, inset 0 0 0 1px ${palette.rim}`,
            }}
          >
            <div
              className="absolute inset-[22%] rounded-full"
              style={{ background: `radial-gradient(circle, ${palette.core} 0%, transparent 70%)` }}
            />
          </div>
        </motion.div>

        <AnimatePresence>
          {showValue && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="pointer-events-none absolute bottom-0 left-1/2 z-20 -translate-x-1/2 translate-y-[calc(100%+6px)] text-[10px] font-medium tabular-nums text-white/75"
            >
              {value}
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {showTooltip && (
          <motion.div
            id={tooltipId}
            role="tooltip"
            initial={{ opacity: 0, x: 6 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 4 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className={cn(
              'pointer-events-none absolute right-[calc(100%+10px)] top-1/2 z-30 w-[9.5rem] -translate-y-1/2',
              'rounded-xl border border-white/10 bg-[rgba(12,14,20,0.88)] px-3 py-2.5',
              'shadow-[0_12px_40px_rgba(0,0,0,0.45)] backdrop-blur-xl',
            )}
          >
            <p className="text-[11px] font-medium tabular-nums text-white/92">Trust {value}</p>
            <p className="mt-1 text-[10px] leading-relaxed text-white/55">{levelName}</p>
            <p className="mt-1.5 text-[10px] text-white/40">
              {editable ? 'Developer 可编辑' : '只读'}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/** @deprecated 使用 IntimacyBar */
export const RelationshipOrb = IntimacyBar
