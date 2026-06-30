import { type PointerEvent, useCallback, useEffect, useRef, useState } from 'react'
import { cn } from '../../lib/cn'
import type { TrustSnapshot } from '../../lib/trustApi'

/** 中间实粉、向两侧渐淡为透明粉 */
const PINK_FILL =
  'linear-gradient(90deg, rgba(255,120,170,0) 0%, rgba(255,145,195,0.98) 50%, rgba(255,120,170,0) 100%)'

type IntimacyBarProps = {
  trust: TrustSnapshot | null
  editable: boolean
  saving?: boolean
  deltaFlash?: number | null
  onChange?: (value: number) => void
  className?: string
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
  const [dragValue, setDragValue] = useState<number | null>(null)

  const min = trust?.min ?? 0
  const max = trust?.max ?? 100
  const committed = trust?.trust_points ?? min
  const value = dragValue ?? committed
  const span = Math.max(1, max - min)
  const percent = ((value - min) / span) * 100
  const showDelta = deltaFlash != null && deltaFlash !== 0

  useEffect(() => {
    if (!draggingRef.current) {
      setDragValue(null)
    }
  }, [committed])

  const valueFromClientY = useCallback(
    (clientY: number) => {
      const track = trackRef.current
      if (!track) return value
      const rect = track.getBoundingClientRect()
      const ratio = 1 - (clientY - rect.top) / rect.height
      const next = min + ratio * span
      return Math.round(Math.max(min, Math.min(max, next)))
    },
    [min, max, span, value],
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
    const finalValue = valueFromClientY(event.clientY)
    setDragValue(null)
    onChange?.(finalValue)
  }

  return (
    <div
      className={cn(
        'flex w-12 shrink-0 flex-col items-center gap-2 rounded-3xl border border-white/20',
        'bg-[linear-gradient(180deg,rgba(243,237,228,0.08)_0%,rgba(243,237,228,0.55)_55%,rgba(243,237,228,0.9)_100%)]',
        'px-2 py-3 backdrop-blur-xl select-none',
        className,
      )}
      aria-label="亲密度"
    >
      <span className="pointer-events-none text-[10px] font-medium tracking-[0.2em] text-white/85 [text-shadow:0_1px_8px_rgba(0,0,0,0.45)] [writing-mode:vertical-rl]">
        亲密度
      </span>

      <div
        ref={trackRef}
        className={cn(
          'relative mt-1 flex min-h-[160px] w-full flex-1 items-stretch justify-center',
          editable ? 'cursor-ns-resize touch-none' : 'cursor-default',
          saving && 'opacity-70',
        )}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishDrag}
        onPointerCancel={finishDrag}
        role={editable ? 'slider' : 'progressbar'}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-readonly={!editable}
        aria-label="亲密度进度"
      >
        {showDelta && (
          <span
            className={cn(
              'pointer-events-none absolute -top-1 left-1/2 z-10 -translate-x-1/2 text-xs font-semibold tabular-nums animate-bounce',
              deltaFlash! < 0 ? 'text-rose-300' : 'text-emerald-200',
            )}
          >
            {deltaFlash! > 0 ? `+${deltaFlash}` : deltaFlash}
          </span>
        )}
        <div className="pointer-events-none relative h-full w-3 rounded-full bg-white/12">
          <div
            className={cn(
              'absolute inset-x-0 bottom-0 rounded-full shadow-[0_0_16px_rgba(255,120,170,0.42)]',
              showDelta ? 'duration-700 transition-[height]' : 'duration-150 transition-[height]',
            )}
            style={{
              height: `${percent}%`,
              background: PINK_FILL,
            }}
          />
          {editable && (
            <div
              className="absolute left-1/2 h-3.5 w-3.5 -translate-x-1/2 rounded-full border border-white/80 bg-[#ffc4dc] shadow-[0_0_12px_rgba(255,120,170,0.65)]"
              style={{ bottom: `calc(${percent}% - 7px)` }}
            />
          )}
        </div>
      </div>

      <span className="pointer-events-none text-[11px] font-medium tabular-nums text-white/90 [text-shadow:0_1px_8px_rgba(0,0,0,0.45)]">
        {value}
      </span>
    </div>
  )
}
