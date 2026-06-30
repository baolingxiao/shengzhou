import { useCallback, useEffect, useRef, useState } from 'react'
import { trace } from '../lib/debugTrace'
import {
  LISTEN_PROMPT,
  SilenceDetector,
  pcmDurationSeconds,
  pcmTail,
  pcmToWavBlob,
  startMicCapture,
} from '../lib/pcmAudio'
import {
  fetchVoiceStatus,
  playTtsChunks,
  synthesizeSpeech,
  transcribeAudio,
  type VoiceStatus,
} from '../lib/voiceApi'

type VoiceState =
  | 'off'
  | 'armed'
  | 'followup'
  | 'capturing'
  | 'processing'
  | 'speaking'

type UseVoiceDialogOptions = {
  enabled: boolean
  chatStatus: 'offline' | 'ready' | 'thinking'
  onUserTranscript: (text: string) => Promise<string | null>
  onVoiceError: (message: string) => void
}

export function useVoiceDialog({
  enabled,
  chatStatus,
  onUserTranscript,
  onVoiceError,
}: UseVoiceDialogOptions) {
  const [active, setActive] = useState(false)
  const [voiceState, setVoiceState] = useState<VoiceState>('off')
  const [statusHint, setStatusHint] = useState('')
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null)
  const [loading, setLoading] = useState(false)

  const stateRef = useRef<VoiceState>('off')
  const configRef = useRef<VoiceStatus | null>(null)
  const micRef = useRef<{ stop: () => void } | null>(null)
  const armedBufferRef = useRef<Uint8Array>(new Uint8Array(0))
  const captureBufferRef = useRef<Uint8Array>(new Uint8Array(0))
  const armedVadRef = useRef<SilenceDetector | null>(null)
  const captureVadRef = useRef<SilenceDetector | null>(null)
  const awaitingQuestionRef = useRef(false)
  const followupTimerRef = useRef<number | null>(null)
  const awaitTimerRef = useRef<number | null>(null)
  const sttBusyRef = useRef(false)
  const enterFollowupRef = useRef<() => void>(() => {})
  const emitStatusRef = useRef<() => void>(() => {})

  const clearTimers = useCallback(() => {
    if (followupTimerRef.current !== null) {
      window.clearTimeout(followupTimerRef.current)
      followupTimerRef.current = null
    }
    if (awaitTimerRef.current !== null) {
      window.clearTimeout(awaitTimerRef.current)
      awaitTimerRef.current = null
    }
  }, [])

  const setState = useCallback((next: VoiceState) => {
    stateRef.current = next
    setVoiceState(next)
    trace('voice.state', { state: next })
  }, [])

  const resetCaptureBuffers = useCallback(() => {
    captureBufferRef.current = new Uint8Array(0)
    captureVadRef.current?.reset()
  }, [])

  const resetBuffers = useCallback(() => {
    armedBufferRef.current = new Uint8Array(0)
    armedVadRef.current?.reset()
    resetCaptureBuffers()
  }, [resetCaptureBuffers])

  const emitStatusForState = useCallback(() => {
    const cfg = configRef.current
    if (!cfg) return
    if (stateRef.current === 'armed') {
      if (awaitingQuestionRef.current) {
        setStatusHint(LISTEN_PROMPT)
        return
      }
      const sample = cfg.wake_phrases.slice(0, 2).join('、') || '在不'
      setStatusHint(`说「${sample}」开始对话`)
      return
    }
    if (stateRef.current === 'followup') {
      setStatusHint('继续说吧（免唤醒）')
      return
    }
    if (stateRef.current === 'off') {
      setStatusHint('')
    }
  }, [])

  useEffect(() => {
    emitStatusRef.current = emitStatusForState
  }, [emitStatusForState])

  const speakText = useCallback(
    async (text: string, fromVoiceDialog: boolean) => {
      const content = text.trim()
      if (!content || !configRef.current?.tts_available) {
        if (fromVoiceDialog) enterFollowupRef.current()
        return
      }
      setState('speaking')
      setStatusHint('说话中…')
      try {
        const chunks = await synthesizeSpeech(content)
        await playTtsChunks(chunks)
      } catch (err) {
        onVoiceError(err instanceof Error ? err.message : 'TTS 播放失败')
      } finally {
        if (fromVoiceDialog) {
          enterFollowupRef.current()
        } else if (stateRef.current === 'speaking') {
          setState('armed')
          emitStatusRef.current()
        }
      }
    },
    [onVoiceError, setState],
  )

  const enterFollowup = useCallback(() => {
    const cfg = configRef.current
    if (!cfg) return
    awaitingQuestionRef.current = false
    if (awaitTimerRef.current !== null) {
      window.clearTimeout(awaitTimerRef.current)
      awaitTimerRef.current = null
    }
    resetBuffers()
    setState('followup')
    setStatusHint('继续说吧（免唤醒）')
    followupTimerRef.current = window.setTimeout(() => {
      if (stateRef.current !== 'followup') return
      setState('armed')
      emitStatusRef.current()
    }, cfg.followup_seconds * 1000)
  }, [resetBuffers, setState])

  useEffect(() => {
    enterFollowupRef.current = enterFollowup
  }, [enterFollowup])

  const submitTranscript = useCallback(
    async (transcript: string) => {
      const text = transcript.trim()
      if (!text) {
        enterFollowup()
        return
      }
      setState('processing')
      setStatusHint('想想…')
      const reply = await onUserTranscript(text)
      if (reply) {
        await speakText(reply, true)
      } else {
        enterFollowup()
      }
    },
    [enterFollowup, onUserTranscript, setState, speakText],
  )

  const finalizeCapture = useCallback(async () => {
    if (sttBusyRef.current) return
    const cfg = configRef.current
    const pcm = captureBufferRef.current
    resetCaptureBuffers()
    const duration = pcmDurationSeconds(pcm.length)
    if (!cfg || duration < cfg.min_speech_seconds) {
      if (awaitingQuestionRef.current) {
        setStatusHint(LISTEN_PROMPT)
      } else {
        emitStatusRef.current()
      }
      return
    }
    awaitingQuestionRef.current = false
    if (awaitTimerRef.current !== null) {
      window.clearTimeout(awaitTimerRef.current)
      awaitTimerRef.current = null
    }
    setState('processing')
    setStatusHint('识别中…')
    sttBusyRef.current = true
    try {
      const result = await transcribeAudio(pcmToWavBlob(pcm), 'utterance')
      if (!result.text.trim()) {
        enterFollowup()
        return
      }
      await submitTranscript(result.text)
    } catch (err) {
      onVoiceError(err instanceof Error ? err.message : '语音识别失败')
      enterFollowup()
    } finally {
      sttBusyRef.current = false
    }
  }, [enterFollowup, onVoiceError, resetCaptureBuffers, setState, submitTranscript])

  const checkWakeAsync = useCallback(
    async (pcm: Uint8Array) => {
      const cfg = configRef.current
      if (!cfg || sttBusyRef.current) return
      setStatusHint('识别唤醒词…')
      sttBusyRef.current = true
      try {
        const tail = pcmTail(pcm, cfg.wake_stt_max_seconds)
        const result = await transcribeAudio(pcmToWavBlob(tail), 'wake')
        if (stateRef.current !== 'armed') return
        if (!result.wake_phrase) {
          emitStatusRef.current()
          return
        }
        awaitingQuestionRef.current = true
        awaitTimerRef.current = window.setTimeout(() => {
          if (!awaitingQuestionRef.current || stateRef.current !== 'armed') return
          awaitingQuestionRef.current = false
          resetCaptureBuffers()
          emitStatusRef.current()
        }, cfg.wake_timeout_seconds * 1000)
        resetCaptureBuffers()
        setStatusHint(LISTEN_PROMPT)
        void speakText(LISTEN_PROMPT, false)
        if (result.cleaned_text && !result.is_wake_only) {
          await submitTranscript(result.cleaned_text)
        }
      } catch (err) {
        onVoiceError(err instanceof Error ? err.message : '唤醒词识别失败')
        emitStatusRef.current()
      } finally {
        sttBusyRef.current = false
      }
    },
    [onVoiceError, resetCaptureBuffers, speakText, submitTranscript],
  )

  const onFrame = useCallback(
    (frame: Uint8Array) => {
      const cfg = configRef.current
      if (!cfg) return
      const state = stateRef.current
      if (state === 'off' || state === 'processing' || state === 'speaking') return

      if (state === 'followup') {
        const merged = new Uint8Array(captureBufferRef.current.length + frame.length)
        merged.set(captureBufferRef.current)
        merged.set(frame, captureBufferRef.current.length)
        captureBufferRef.current = merged
        if (captureVadRef.current?.feed(frame) === 'utterance_end') {
          void finalizeCapture()
        }
        return
      }

      if (state === 'armed') {
        if (awaitingQuestionRef.current) {
          const merged = new Uint8Array(captureBufferRef.current.length + frame.length)
          merged.set(captureBufferRef.current)
          merged.set(frame, captureBufferRef.current.length)
          captureBufferRef.current = merged
          if (captureVadRef.current?.feed(frame) === 'utterance_end') {
            void finalizeCapture()
          }
          return
        }

        const merged = new Uint8Array(armedBufferRef.current.length + frame.length)
        merged.set(armedBufferRef.current)
        merged.set(frame, armedBufferRef.current.length)
        armedBufferRef.current = merged
        const maxBytes = Math.floor(cfg.wake_stt_max_seconds * 16_000 * 2)
        if (armedBufferRef.current.length > maxBytes) {
          armedBufferRef.current = armedBufferRef.current.slice(-maxBytes)
        }
        if (armedVadRef.current?.feed(frame) === 'utterance_end') {
          const pcm = armedBufferRef.current
          armedBufferRef.current = new Uint8Array(0)
          armedVadRef.current.reset()
          void checkWakeAsync(pcm)
        }
      }
    },
    [checkWakeAsync, finalizeCapture],
  )

  const stopSession = useCallback(() => {
    clearTimers()
    micRef.current?.stop()
    micRef.current = null
    resetBuffers()
    awaitingQuestionRef.current = false
    setState('off')
    setStatusHint('')
    setActive(false)
  }, [clearTimers, resetBuffers, setState])

  const startSession = useCallback(async () => {
    setLoading(true)
    try {
      const status = await fetchVoiceStatus()
      setVoiceStatus(status)
      configRef.current = status
      if (!status.stt_available) {
        throw new Error(status.stt_reason || '语音识别不可用')
      }
      if (!status.tts_available) {
        throw new Error(status.tts_reason || '语音播报不可用，语音对话需要 ElevenLabs TTS')
      }
      armedVadRef.current = new SilenceDetector(
        status.wake_silence_seconds,
        Math.min(status.min_speech_seconds, 0.25),
        450,
      )
      captureVadRef.current = new SilenceDetector(
        status.silence_seconds,
        status.min_speech_seconds,
        450,
      )
      resetBuffers()
      const mic = await startMicCapture(onFrame)
      micRef.current = mic
      setState('armed')
      emitStatusRef.current()
      setActive(true)
      trace('voice.session.start')
    } catch (err) {
      onVoiceError(err instanceof Error ? err.message : '无法启动语音对话')
      stopSession()
    } finally {
      setLoading(false)
    }
  }, [onFrame, onVoiceError, resetBuffers, setState, stopSession])

  const toggle = useCallback(async () => {
    if (active) {
      stopSession()
      return
    }
    await startSession()
  }, [active, startSession, stopSession])

  const notifyChatFailed = useCallback(() => {
    if (!active || stateRef.current !== 'processing') return
    enterFollowup()
  }, [active, enterFollowup])

  useEffect(() => {
    if (!enabled && active) {
      stopSession()
    }
  }, [active, enabled, stopSession])

  useEffect(() => {
    if (!active) return
    if (chatStatus === 'thinking' && stateRef.current === 'processing') {
      setStatusHint('想想…')
    }
  }, [active, chatStatus])

  useEffect(() => {
    return () => {
      stopSession()
    }
  }, [stopSession])

  return {
    active,
    loading,
    voiceState,
    statusHint,
    voiceStatus,
    toggle,
    notifyChatFailed,
    available: Boolean(voiceStatus?.stt_available && voiceStatus?.tts_available),
  }
}
