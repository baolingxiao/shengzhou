import { motion } from 'motion/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { trace, traceStateChange } from '../../lib/debugTrace'
import { ScreenCurtain } from './ScreenCurtain'
import { NeuralInterface } from './NeuralInterface'
import { ShenzhouAdminButton } from '../admin/ShenzhouAdminButton'
import { MacPermissionsButton } from '../system/MacPermissionsButton'
import { UserProfileButton } from '../user/UserProfileButton'
import { RoseTwo } from './RoseTwo'
import { StartGate } from './StartGate'
import { WakeupAudio, type PlayWakeupAudio } from './WakeupAudio'
import { WakeupText } from './WakeupText'
import { OceanBackground } from '../ocean/OceanBackground'
import { OceanBackgroundBgm } from '../ocean/OceanBackgroundBgm'
import { CinematicAtmosphere } from '../ocean/CinematicAtmosphere'
import { SolidBackground } from '../ocean/SolidBackground'
import { BackgroundModeToggle } from '../ocean/BackgroundModeToggle'
import { useBackgroundMode } from '../../hooks/useBackgroundMode'
import {
  DEFAULT_AUDIO_DURATION_SEC,
  EASE_OUT_EXPO,
  buildTimeline,
  contentOpacityAtTime,
  grayscaleAtTime,
  phaseAtTime,
  type WakeupPhase,
} from '../../motion/timing'

type BootPhase = 'loading-audio' | 'awaiting-start' | 'running'

type NeuralWakeupProps = {
  userName?: string
  authenticated?: boolean
  role?: 'developer' | 'user' | null
  loginError?: string | null
  loggingIn?: boolean
  onLogin?: (username: string, password: string) => Promise<void>
  onRegister?: (username: string, password: string) => Promise<void>
  onLogout?: () => void
  onOpenProfile?: () => void
  personaRequired?: boolean
  personaConfigured?: boolean
  personaLoading?: boolean
  personaSaving?: boolean
  personaError?: string | null
  onSavePersona?: (
    displayName: string,
    stylePrompt: string,
    apiKeys: {
      chatgptApiKey: string
      claudeApiKey: string
      deepseekApiKey: string
      doubaoApiKey: string
    },
  ) => Promise<void>
  onComplete?: () => void
}

export function NeuralWakeup({
  userName = 'Jin',
  authenticated = false,
  role = null,
  loginError = null,
  loggingIn = false,
  onLogin,
  onRegister,
  onLogout,
  onOpenProfile,
  personaRequired = false,
  personaConfigured = true,
  personaLoading = false,
  personaSaving = false,
  personaError = null,
  onSavePersona,
  onComplete,
}: NeuralWakeupProps) {
  const [bootPhase, setBootPhase] = useState<BootPhase>('loading-audio')
  const [phase, setPhase] = useState<WakeupPhase>('blackout')
  const [elapsed, setElapsed] = useState(0)
  const [sequenceStart, setSequenceStart] = useState<number | null>(null)
  const [audioDuration, setAudioDuration] = useState(DEFAULT_AUDIO_DURATION_SEC)
  const [chatUnlocked, setChatUnlocked] = useState(false)
  const [ambientUnlocked, setAmbientUnlocked] = useState(false)
  const playAudioRef = useRef<PlayWakeupAudio | null>(null)
  const completeRef = useRef(false)
  const chatUnlockLogged = useRef(false)
  const prevBootPhase = useRef(bootPhase)
  const prevPhase = useRef(phase)
  const prevChatUnlocked = useRef(chatUnlocked)

  useEffect(() => {
    trace('wakeup.mount')
    return () => {
      trace('wakeup.unmount', {}, 'warn')
    }
  }, [])

  useEffect(() => {
    traceStateChange('wakeup.state', 'bootPhase', prevBootPhase.current, bootPhase, {
      chatUnlocked,
      phase,
    })
    prevBootPhase.current = bootPhase
  }, [bootPhase, chatUnlocked, phase])

  useEffect(() => {
    traceStateChange('wakeup.state', 'phase', prevPhase.current, phase, {
      bootPhase,
      chatUnlocked,
      elapsed: Number(elapsed.toFixed(2)),
    })
    prevPhase.current = phase
  }, [phase, bootPhase, chatUnlocked, elapsed])

  useEffect(() => {
    traceStateChange('wakeup.state', 'chatUnlocked', prevChatUnlocked.current, chatUnlocked, {
      bootPhase,
      phase,
    })
    prevChatUnlocked.current = chatUnlocked
  }, [chatUnlocked, bootPhase, phase])

  useEffect(() => {
    if (bootPhase !== 'running' && chatUnlocked) {
      trace(
        'wakeup.anomaly.start_gate_with_chat_unlocked',
        { bootPhase, chatUnlocked, phase },
        'alert',
      )
    }
  }, [bootPhase, chatUnlocked, phase])

  const timeline = useMemo(() => buildTimeline(audioDuration), [audioDuration])

  const handleAudioReady = useCallback((play: PlayWakeupAudio, durationSec: number) => {
    trace('wakeup.audio_ready', { durationSec, bootPhase })
    playAudioRef.current = play
    setAudioDuration(durationSec)
    // Never rewind to start screen once the wakeup sequence is running.
    setBootPhase((prev) => {
      const next = prev === 'loading-audio' ? 'awaiting-start' : prev
      if (prev !== next) {
        trace('wakeup.audio_ready.set_boot_phase', { from: prev, to: next })
      }
      return next
    })
  }, [])

  const handleStart = useCallback(async () => {
    trace('wakeup.start_click', { bootPhase, hasPlayer: Boolean(playAudioRef.current) })
    if (bootPhase !== 'awaiting-start' || !playAudioRef.current) return

    setAmbientUnlocked(true)
    setBootPhase('running')
    const start = performance.now()
    setSequenceStart(start)
    setPhase('blackout')
    setElapsed(0)
    completeRef.current = false
    trace('wakeup.sequence_started', { start })

    const played = await playAudioRef.current()
    trace('wakeup.audio_play_result', { played })
  }, [bootPhase])

  useEffect(() => {
    if (bootPhase !== 'running' || sequenceStart === null) return

    let cancelled = false
    let raf = 0
    const start = sequenceStart

    const tick = (now: number) => {
      if (cancelled) return

      const t = (now - start) / 1000
      const nextPhase = phaseAtTime(t, audioDuration)
      setElapsed(t)
      setPhase(nextPhase)
      if (nextPhase === 'finale') {
        setChatUnlocked(true)
        if (!chatUnlockLogged.current) {
          chatUnlockLogged.current = true
          trace('wakeup.chat_unlocked', { t: Number(t.toFixed(2)) })
        }
      }

      if (t < timeline.sequenceEnd) {
        raf = requestAnimationFrame(tick)
      } else if (!completeRef.current) {
        completeRef.current = true
        trace('wakeup.sequence_complete', {
          t: Number(t.toFixed(2)),
          chatUnlocked: true,
        })
        onComplete?.()
      }
    }

    raf = requestAnimationFrame(tick)

    return () => {
      cancelled = true
      cancelAnimationFrame(raf)
      trace('wakeup.tick_loop_cancelled', { bootPhase, sequenceStart })
    }
  }, [bootPhase, sequenceStart, onComplete, audioDuration, timeline.sequenceEnd])

  const showFinale = phase === 'finale'
  const roseFaded = showFinale
  const isRunning = bootPhase === 'running'

  const revealOpacity = contentOpacityAtTime(elapsed)
  const revealGrayscale = grayscaleAtTime(elapsed)
  const { mode: bgMode, toggle: toggleBg, isOcean } = useBackgroundMode()

  /** 加载 / 唤醒页结束后才允许海洋 BGM（与 chatUnlocked 同步） */
  const oceanBgmEnabled = chatUnlocked && isOcean

  return (
    <div className="relative min-h-full overflow-hidden">
      <CinematicAtmosphere oceanBlend={isOcean} />
      <SolidBackground active={!isOcean} />
      <OceanBackgroundBgm active={oceanBgmEnabled} unlocked={ambientUnlocked} />
      <OceanBackground active={isOcean} />

      <BackgroundModeToggle
        mode={bgMode}
        onToggle={toggleBg}
        className="absolute right-4 top-4 z-50 md:right-6 md:top-6"
      />

      {onOpenProfile && chatUnlocked && (
        <UserProfileButton
          onClick={onOpenProfile}
          className="absolute left-4 top-4 z-50 md:left-6 md:top-6"
        />
      )}

      <StartGate
        visible={bootPhase !== 'running'}
        loading={bootPhase === 'loading-audio'}
        authenticated={authenticated}
        role={role}
        loggingIn={loggingIn}
        loginError={loginError}
        personaRequired={personaRequired}
        personaConfigured={personaConfigured}
        personaLoading={personaLoading}
        personaSaving={personaSaving}
        personaError={personaError}
        onOpenProfile={onOpenProfile}
        onLogin={async (user, pass) => {
          await onLogin?.(user, pass)
        }}
        onRegister={async (user, pass) => {
          await onRegister?.(user, pass)
        }}
        onSavePersona={async (displayName, stylePrompt, apiKeys) => {
          await onSavePersona?.(displayName, stylePrompt, apiKeys)
        }}
        onStart={() => void handleStart()}
      />

      {isRunning && <ScreenCurtain elapsed={elapsed} />}
      <WakeupAudio onReady={handleAudioReady} />

      {sequenceStart !== null && (
        <div
          className="pointer-events-none absolute left-1/2 top-[20vh] z-10 w-[min(72vmin,420px)] -translate-x-1/2 md:top-[18vh]"
          style={{
            opacity: revealOpacity,
            filter: `grayscale(${revealGrayscale})`,
          }}
        >
          <WakeupText
            visible={showFinale}
            name={userName}
            className="absolute bottom-[calc(100%+1rem)] left-1/2 w-[max(100%,280px)] -translate-x-1/2"
          />

          <motion.div
            animate={roseFaded ? { opacity: 0.35, scale: 0.92 } : { opacity: 1, scale: 1 }}
            transition={{ duration: 1.2, ease: EASE_OUT_EXPO }}
          >
            <RoseTwo startedAt={sequenceStart} />
          </motion.div>

          {!chatUnlocked && (
            <div className="pointer-events-none mt-6 text-center">
              <p className="text-[22px] font-light tracking-[-0.03em] text-jarvis-text">Jarvis</p>
              <p className="mt-1.5 text-[13px] tracking-[0.02em] text-jarvis-greeting">
                An AI That Lives With You
              </p>
            </div>
          )}
        </div>
      )}

      <NeuralInterface visible={chatUnlocked} onLogout={onLogout} />

      <ShenzhouAdminButton visible={chatUnlocked && role === 'developer'} />
      <MacPermissionsButton visible={chatUnlocked} />

      {import.meta.env.DEV && isRunning && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-[60] font-mono text-[10px] text-muted/50">
          {elapsed.toFixed(1)}s · {phase} · audio {audioDuration.toFixed(1)}s
        </div>
      )}
    </div>
  )
}
