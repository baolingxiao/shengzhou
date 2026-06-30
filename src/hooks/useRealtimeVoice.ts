import { useCallback, useEffect, useRef, useState } from 'react'
import { createRealtimeSession } from '../lib/realtimeApi'
import { OPENAI_REALTIME_CALLS_URL } from '../lib/realtimeConfig'
import { DEFAULT_CHARACTER_ID } from '../lib/characterConfig'

export type RealtimeVoiceStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'speaking'
  | 'error'

type UseRealtimeVoiceOptions = {
  enabled: boolean
  sessionId: string
  characterId?: string
  onError?: (message: string) => void
}

function log(msg: string, extra?: unknown) {
  if (extra !== undefined) {
    console.log(`[RealtimeVoice] ${msg}`, extra)
  } else {
    console.log(`[RealtimeVoice] ${msg}`)
  }
}

export function useRealtimeVoice({
  enabled,
  sessionId,
  characterId = DEFAULT_CHARACTER_ID,
  onError,
}: UseRealtimeVoiceOptions) {
  const [status, setStatus] = useState<RealtimeVoiceStatus>('idle')
  const [error, setError] = useState<string | null>(null)

  const pcRef = useRef<RTCPeerConnection | null>(null)
  const dcRef = useRef<RTCDataChannel | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const audioElRef = useRef<HTMLAudioElement | null>(null)
  const activeRef = useRef(false)

  const setErr = useCallback(
    (message: string) => {
      log('error', message)
      setError(message)
      setStatus('error')
      onError?.(message)
    },
    [onError],
  )

  const cleanup = useCallback(() => {
    dcRef.current?.close()
    dcRef.current = null

    pcRef.current?.close()
    pcRef.current = null

    micStreamRef.current?.getTracks().forEach((t) => t.stop())
    micStreamRef.current = null

    if (audioElRef.current) {
      audioElRef.current.pause()
      audioElRef.current.srcObject = null
      audioElRef.current.remove()
      audioElRef.current = null
    }

    activeRef.current = false
  }, [])

  const sendEvent = useCallback((event: Record<string, unknown>) => {
    const dc = dcRef.current
    if (dc?.readyState === 'open') {
      dc.send(JSON.stringify(event))
    }
  }, [])

  const handleServerEvent = useCallback((raw: string) => {
    let event: { type?: string }
    try {
      event = JSON.parse(raw) as { type?: string }
    } catch {
      return
    }
    log('event received', event.type)
    const t = event.type ?? ''
    if (t === 'session.created' || t === 'session.updated') {
      setStatus('listening')
    } else if (
      t === 'response.output_audio.delta' ||
      t === 'response.audio.delta' ||
      t === 'output_audio_buffer.started'
    ) {
      setStatus('speaking')
    } else if (t === 'response.done' || t === 'output_audio_buffer.stopped') {
      setStatus('listening')
    } else if (t === 'error') {
      setErr('Realtime 服务端错误')
    }
  }, [setErr])

  const stopRealtimeVoice = useCallback(() => {
    log('stopped')
    cleanup()
    setStatus('idle')
    setError(null)
  }, [cleanup])

  const interrupt = useCallback(() => {
    log('interrupted')
    sendEvent({ type: 'response.cancel' })
    const audio = audioElRef.current
    if (audio) {
      audio.pause()
      try {
        audio.currentTime = 0
      } catch {
        /* ignore */
      }
    }
    setStatus('listening')
  }, [sendEvent])

  const sendTextEvent = useCallback(
    (text: string) => {
      const content = text.trim()
      if (!content) return
      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'message',
          role: 'user',
          content: [{ type: 'input_text', text: content }],
        },
      })
      sendEvent({ type: 'response.create' })
    },
    [sendEvent],
  )

  const startRealtimeVoice = useCallback(async () => {
    if (activeRef.current) return
    activeRef.current = true
    setError(null)
    setStatus('connecting')

    try {
      log('creating session')
      const session = await createRealtimeSession({
        characterId,
        sessionId,
        mode: 'voice_chat',
      })

      log('microphone ready')
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      micStreamRef.current = micStream

      log('peer connection created')
      const pc = new RTCPeerConnection()
      pcRef.current = pc

      const audioEl = document.createElement('audio')
      audioEl.autoplay = true
      audioEl.setAttribute('playsinline', 'true')
      document.body.appendChild(audioEl)
      audioElRef.current = audioEl

      pc.ontrack = (e) => {
        const stream = e.streams[0]
        if (stream && audioElRef.current) {
          audioElRef.current.srcObject = stream
          void audioElRef.current.play().catch(() => {
            setErr('浏览器阻止自动播放，请点击页面后重试')
          })
        }
      }

      pc.onconnectionstatechange = () => {
        const state = pc.connectionState
        if (state === 'connected') {
          log('connected')
          setStatus('connected')
        } else if (state === 'failed' || state === 'disconnected') {
          setErr(`WebRTC 连接 ${state}`)
        }
      }

      micStream.getTracks().forEach((track) => pc.addTrack(track, micStream))

      const dc = pc.createDataChannel('oai-events')
      dcRef.current = dc
      dc.onopen = () => log('data channel open')
      dc.onmessage = (e) => handleServerEvent(String(e.data))

      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)

      const sdpResponse = await fetch(OPENAI_REALTIME_CALLS_URL, {
        method: 'POST',
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${session.client_secret}`,
          'Content-Type': 'application/sdp',
        },
      })

      if (!sdpResponse.ok) {
        const detail = await sdpResponse.text()
        throw new Error(
          detail || `WebRTC SDP 交换失败 (${sdpResponse.status})`,
        )
      }

      const answerSdp = await sdpResponse.text()
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp })

      setStatus('listening')
    } catch (err) {
      activeRef.current = false
      cleanup()
      const message =
        err instanceof Error ? err.message : 'Realtime 语音连接失败'
      if (message.includes('Permission') || message.includes('NotAllowed')) {
        setErr('麦克风权限被拒绝，请在浏览器设置中允许麦克风')
      } else {
        setErr(message)
      }
    }
  }, [
    characterId,
    cleanup,
    handleServerEvent,
    sessionId,
    setErr,
  ])

  useEffect(() => {
    if (!enabled && activeRef.current) {
      stopRealtimeVoice()
    }
  }, [enabled, stopRealtimeVoice])

  useEffect(() => () => stopRealtimeVoice(), [stopRealtimeVoice])

  const isConnected =
    status === 'connected' ||
    status === 'listening' ||
    status === 'speaking'

  return {
    status,
    isConnected,
    isSpeaking: status === 'speaking',
    error,
    startRealtimeVoice,
    stopRealtimeVoice,
    interrupt,
    sendTextEvent,
  }
}
