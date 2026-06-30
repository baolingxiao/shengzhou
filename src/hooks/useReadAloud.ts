import { useCallback, useEffect, useRef, useState } from 'react'
import { getActiveTraceId } from '../lib/executionTrace'
import { trace } from '../lib/debugTrace'
import {
  fetchVoiceStatus,
  playTtsChunks,
  synthesizeSpeech,
} from '../lib/voiceApi'

const STORAGE_KEY = 'jarvis-read-aloud'

export function useReadAloud(
  enabled: boolean,
  onError: (message: string) => void,
) {
  const [on, setOn] = useState(() => localStorage.getItem(STORAGE_KEY) === '1')
  const [available, setAvailable] = useState<boolean | null>(null)
  const [reason, setReason] = useState('')
  const [speaking, setSpeaking] = useState(false)
  const onRef = useRef(on)
  onRef.current = on

  useEffect(() => {
    if (!enabled) return
    void fetchVoiceStatus()
      .then((status) => {
        setAvailable(status.tts_available)
        setReason(status.tts_reason)
      })
      .catch(() => {
        setAvailable(false)
        setReason('无法连接语音服务')
      })
  }, [enabled])

  const speak = useCallback(
    async (text: string) => {
      const content = text.trim()
      if (!onRef.current || !content) return
      setSpeaking(true)
      trace('read_aloud.start', { len: content.length })
      const traceId = getActiveTraceId()
      try {
        const chunks = await synthesizeSpeech(content, traceId)
        await playTtsChunks(chunks, traceId)
        trace('read_aloud.done')
      } catch (err) {
        const message =
          err instanceof Error ? err.message : '文字朗读失败'
        trace('read_aloud.error', { message }, 'alert')
        onError(message)
      } finally {
        setSpeaking(false)
      }
    },
    [onError],
  )

  const toggle = useCallback(async () => {
    const next = !onRef.current
    if (next) {
      try {
        const status = await fetchVoiceStatus()
        setAvailable(status.tts_available)
        setReason(status.tts_reason)
        if (!status.tts_available) {
          throw new Error(
            status.tts_reason ||
              '文字朗读不可用，请配置 ELEVENLABS_API_KEY 与 ELEVENLABS_VOICE_ID',
          )
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : '无法开启文字朗读'
        onError(message)
        return
      }
    }
    setOn(next)
    localStorage.setItem(STORAGE_KEY, next ? '1' : '0')
    trace('read_aloud.toggle', { on: next })
  }, [onError])

  return {
    on,
    toggle,
    speak,
    speaking,
    available,
    reason,
  }
}
