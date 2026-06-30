import { useCallback, useEffect, useRef, useState } from 'react'
import {
  SilenceDetector,
  pcmToWavBlob,
  startMicCapture,
} from '../lib/pcmAudio'
import { fetchVoiceStatus, transcribeAudio } from '../lib/voiceApi'

type UseVoiceInputOptions = {
  enabled: boolean
  disabled?: boolean
  onTranscript: (text: string) => void
  onError: (message: string) => void
}

export function useVoiceInput({
  enabled,
  disabled = false,
  onTranscript,
  onError,
}: UseVoiceInputOptions) {
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [available, setAvailable] = useState<boolean | null>(null)
  const micRef = useRef<{ stop: () => void } | null>(null)
  const bufferRef = useRef<Uint8Array>(new Uint8Array(0))
  const vadRef = useRef<SilenceDetector | null>(null)
  const busyRef = useRef(false)
  const maxTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!enabled) return
    void fetchVoiceStatus()
      .then((s) => setAvailable(s.stt_available))
      .catch(() => setAvailable(false))
  }, [enabled])

  const stopMic = useCallback(() => {
    if (maxTimerRef.current !== null) {
      window.clearTimeout(maxTimerRef.current)
      maxTimerRef.current = null
    }
    micRef.current?.stop()
    micRef.current = null
    setRecording(false)
  }, [])

  const finishAndTranscribe = useCallback(async () => {
    if (busyRef.current) return
    busyRef.current = true
    setTranscribing(true)
    const pcm = bufferRef.current
    bufferRef.current = new Uint8Array(0)
    vadRef.current?.reset()
    stopMic()

    try {
      if (!pcm.length) {
        onError('没听清，请再试一次')
        return
      }
      const blob = pcmToWavBlob(pcm)
      const result = await transcribeAudio(blob, 'utterance')
      const text = (result.cleaned_text || result.text || '').trim()
      if (!text) {
        onError('没识别到内容')
        return
      }
      onTranscript(text)
    } catch (err) {
      onError(err instanceof Error ? err.message : '语音识别失败')
    } finally {
      busyRef.current = false
      setTranscribing(false)
    }
  }, [onError, onTranscript, stopMic])

  const startRecording = useCallback(async () => {
    if (disabled || busyRef.current || recording) return
    if (available === false) {
      onError('语音输入不可用，请检查后端语音配置')
      return
    }

    try {
      const status = await fetchVoiceStatus()
      if (!status.stt_available) {
        setAvailable(false)
        onError(status.stt_reason || '语音识别未配置')
        return
      }
      setAvailable(true)
      bufferRef.current = new Uint8Array(0)
      vadRef.current = new SilenceDetector(
        status.silence_seconds || 1.2,
        status.min_speech_seconds || 0.35,
      )
      const mic = await startMicCapture((frame) => {
        const merged = new Uint8Array(bufferRef.current.length + frame.length)
        merged.set(bufferRef.current)
        merged.set(frame, bufferRef.current.length)
        bufferRef.current = merged

        const vad = vadRef.current
        if (!vad) return
        const event = vad.feed(frame)
        if (event === 'utterance_end') {
          void finishAndTranscribe()
        }
      })
      micRef.current = mic
      setRecording(true)
      maxTimerRef.current = window.setTimeout(() => {
        void finishAndTranscribe()
      }, 45_000)
    } catch (err) {
      stopMic()
      onError(err instanceof Error ? err.message : '无法访问麦克风')
    }
  }, [available, disabled, finishAndTranscribe, onError, recording, stopMic])

  const toggle = useCallback(() => {
    if (recording) {
      void finishAndTranscribe()
      return
    }
    void startRecording()
  }, [finishAndTranscribe, recording, startRecording])

  useEffect(() => () => stopMic(), [stopMic])

  return {
    recording,
    transcribing,
    available,
    toggle,
    stop: stopMic,
  }
}
