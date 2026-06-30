/** Cinematic easing — Apple-quality deceleration */
export const EASE_OUT_EXPO = [0.22, 1, 0.36, 1] as const

/** Fallback if audio metadata is unavailable */
export const DEFAULT_AUDIO_DURATION_SEC = 12.572

/** Intro — fixed; rose phase fills the remainder until audio ends */
export const TIMELINE = {
  blackoutHold: 1,
  blackoutFade: 5,
  /** Fade-in for text + card at audio end */
  finaleFade: 1.2,
} as const

export type TimelineAbs = {
  introEnd: number
  audioEnd: number
  roseEnd: number
  finaleStart: number
  sequenceEnd: number
}

export function buildTimeline(audioDurationSec: number): TimelineAbs {
  const introEnd = TIMELINE.blackoutHold + TIMELINE.blackoutFade
  const audioEnd = audioDurationSec
  return {
    introEnd,
    audioEnd,
    roseEnd: audioEnd,
    finaleStart: audioEnd,
    sequenceEnd: audioEnd + TIMELINE.finaleFade,
  }
}

/** Decelerating fade — matches motion EASE_OUT_EXPO feel */
export function easeOutExpo(t: number): number {
  if (t <= 0) return 0
  if (t >= 1) return 1
  return 1 - 2 ** (-10 * t)
}

export function curtainOpacityAtTime(elapsed: number): number {
  if (elapsed < TIMELINE.blackoutHold) return 1
  const fadeProgress = (elapsed - TIMELINE.blackoutHold) / TIMELINE.blackoutFade
  if (fadeProgress >= 1) return 0
  return 1 - easeOutExpo(fadeProgress)
}

export function grayscaleAtTime(elapsed: number): number {
  const introEnd = TIMELINE.blackoutHold + TIMELINE.blackoutFade
  if (elapsed < TIMELINE.blackoutHold) return 1
  if (elapsed >= introEnd) return 0
  const fadeProgress = (elapsed - TIMELINE.blackoutHold) / TIMELINE.blackoutFade
  return 1 - easeOutExpo(fadeProgress)
}

export function contentOpacityAtTime(elapsed: number): number {
  const introEnd = TIMELINE.blackoutHold + TIMELINE.blackoutFade
  if (elapsed < TIMELINE.blackoutHold) return 0
  if (elapsed >= introEnd) return 1
  const fadeProgress = (elapsed - TIMELINE.blackoutHold) / TIMELINE.blackoutFade
  return easeOutExpo(fadeProgress)
}

export type WakeupPhase = 'blackout' | 'reveal' | 'rose' | 'finale'

export function phaseAtTime(elapsed: number, audioDurationSec: number): WakeupPhase {
  const { introEnd, audioEnd } = buildTimeline(audioDurationSec)
  if (elapsed < TIMELINE.blackoutHold) return 'blackout'
  if (elapsed < introEnd) return 'reveal'
  if (elapsed < audioEnd) return 'rose'
  return 'finale'
}
