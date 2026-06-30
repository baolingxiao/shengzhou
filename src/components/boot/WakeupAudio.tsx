import { useCallback, useLayoutEffect, useRef } from 'react'
import { trace } from '../../lib/debugTrace'
import { DEFAULT_AUDIO_DURATION_SEC } from '../../motion/timing'

export const WAKEUP_AUDIO_SRC = '/audio/wakeup.m4a'

export type PlayWakeupAudio = () => Promise<boolean>

type WakeupAudioProps = {
  onReady: (play: PlayWakeupAudio, durationSec: number) => void
}

function waitForAudioReady(audio: HTMLAudioElement) {
  if (audio.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
    return Promise.resolve()
  }

  return new Promise<void>((resolve, reject) => {
    const onReady = () => {
      cleanup()
      resolve()
    }
    const onError = () => {
      cleanup()
      reject(new Error('Audio failed to load'))
    }
    const cleanup = () => {
      audio.removeEventListener('canplaythrough', onReady)
      audio.removeEventListener('error', onError)
    }

    audio.addEventListener('canplaythrough', onReady, { once: true })
    audio.addEventListener('error', onError, { once: true })
    audio.load()
  })
}

function readDuration(audio: HTMLAudioElement) {
  return Number.isFinite(audio.duration) && audio.duration > 0
    ? audio.duration
    : DEFAULT_AUDIO_DURATION_SEC
}

export function WakeupAudio({ onReady }: WakeupAudioProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const onReadyRef = useRef(onReady)
  onReadyRef.current = onReady

  const createPlayer = useCallback((): PlayWakeupAudio => {
    return async () => {
      const audio = audioRef.current
      if (!audio) return false

      try {
        audio.currentTime = 0
        await audio.play()
        return true
      } catch {
        return false
      }
    }
  }, [])

  useLayoutEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    let cancelled = false

    const notifyReady = async () => {
      if (cancelled) return
      try {
        await waitForAudioReady(audio)
        if (!cancelled) {
          trace('wakeup.audio.on_ready', { duration: readDuration(audio) })
          onReadyRef.current(createPlayer(), readDuration(audio))
        }
      } catch {
        if (!cancelled) {
          trace('wakeup.audio.on_ready_fallback', { duration: DEFAULT_AUDIO_DURATION_SEC }, 'warn')
          onReadyRef.current(createPlayer(), DEFAULT_AUDIO_DURATION_SEC)
        }
      }
    }

    void notifyReady()

    return () => {
      cancelled = true
      trace('wakeup.audio.effect_cleanup', {}, 'warn')
    }
  }, [createPlayer])

  return (
    <audio
      ref={audioRef}
      src={WAKEUP_AUDIO_SRC}
      preload="auto"
      className="sr-only"
      aria-hidden
    />
  )
}
