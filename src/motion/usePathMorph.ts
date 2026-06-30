import { interpolate } from 'flubber'
import { useMemo } from 'react'

type MorphOptions = {
  maxSegmentLength?: number
}

export function usePathMorph(
  fromPath: string,
  toPath: string,
  progress: number,
  options: MorphOptions = {},
) {
  const { maxSegmentLength = 2 } = options

  const interpolator = useMemo(
    () => interpolate(fromPath, toPath, { maxSegmentLength }),
    [fromPath, toPath, maxSegmentLength],
  )

  const clamped = Math.min(1, Math.max(0, progress))
  return interpolator(clamped)
}

export function useDualMorph(
  startPath: string,
  midPath: string,
  endPath: string,
  progress: number,
) {
  const firstHalf = usePathMorph(startPath, midPath, Math.min(1, progress * 2))
  const secondHalf = usePathMorph(midPath, endPath, Math.max(0, progress * 2 - 1))

  return progress < 0.5 ? firstHalf : secondHalf
}
