import { useCallback, useEffect, useRef } from 'react'
import { cn } from '../../lib/cn'

/** 海洋背景专属 BGM（由录屏视频提取音轨，见 public/audio/ocean-bgm.m4a） */
export const OCEAN_BGM_SRC = '/audio/ocean-bgm.m4a'

const DEFAULT_VOLUME = 0.65

type OceanBackgroundBgmProps = {
  /** 是否允许播放（加载页结束 + 海洋背景） */
  active?: boolean
  /** 用户已与页面交互，允许播放（浏览器 autoplay 策略） */
  unlocked?: boolean
  className?: string
}

/**
 * 隐藏在海洋 Canvas 下方的专属 BGM。
 * 仅在父级判定加载 / 唤醒流程结束后将 active 设为 true。
 */
export function OceanBackgroundBgm({
  active = false,
  unlocked = false,
  className,
}: OceanBackgroundBgmProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const activeRef = useRef(active)
  activeRef.current = active

  const tryPlay = useCallback(() => {
    const audio = audioRef.current
    if (!audio || !activeRef.current) return

    audio.volume = DEFAULT_VOLUME
    void audio.play().catch((err) => {
      if (import.meta.env.DEV) {
        console.warn('[OceanBackgroundBgm] play failed', err)
      }
    })
  }, [])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    if (active && unlocked) {
      tryPlay()
      return
    }

    audio.pause()
  }, [active, unlocked, tryPlay])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const onError = () => {
      if (import.meta.env.DEV) {
        console.warn('[OceanBackgroundBgm] load error', audio.error)
      }
    }

    audio.addEventListener('error', onError)
    return () => audio.removeEventListener('error', onError)
  }, [])

  return (
    <div
      className={cn(
        'pointer-events-none absolute inset-0 z-0 overflow-hidden',
        className,
      )}
      aria-hidden
    >
      <audio
        ref={audioRef}
        src={OCEAN_BGM_SRC}
        loop
        preload="auto"
        className="absolute h-px w-px opacity-0"
        tabIndex={-1}
      />
    </div>
  )
}
