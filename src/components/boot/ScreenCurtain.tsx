import { curtainOpacityAtTime } from '../../motion/timing'

type ScreenCurtainProps = {
  elapsed: number
}

/** Full-viewport black hold (5s), then 5s fade to warm white */
export function ScreenCurtain({ elapsed }: ScreenCurtainProps) {
  const opacity = curtainOpacityAtTime(elapsed)
  if (opacity <= 0) return null

  return (
    <div
      className="pointer-events-none fixed inset-0 z-50 bg-[#050505]"
      style={{ opacity }}
      aria-hidden
    />
  )
}
