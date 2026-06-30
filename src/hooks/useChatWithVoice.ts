import { useCallback, type RefObject } from 'react'
import { useChat } from './useChat'
import { useReadAloud } from './useReadAloud'
import { useVoiceDialog } from './useVoiceDialog'
import { useVoiceInput } from './useVoiceInput'
import { useRealtimeVoice } from './useRealtimeVoice'
import { trace } from '../lib/debugTrace'
import { REALTIME_VOICE_ENABLED } from '../lib/realtimeConfig'
import { DEFAULT_CHARACTER_ID } from '../lib/characterConfig'
import { useUserSession } from '../contexts/UserSessionContext'

export function useChatWithVoice(
  visible: boolean,
  onChatReply?: (reply: import('../lib/chatApi').ChatReply) => void,
  inputRef?: RefObject<HTMLInputElement | null>,
) {
  const { sessionId } = useUserSession()
  const chat = useChat(visible, onChatReply)

  const handleVoiceError = useCallback(
    (message: string) => {
      trace('voice.error', { message }, 'alert')
      chat.setError(message)
    },
    [chat.setError],
  )

  const appendToInput = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      if (!trimmed) return
      chat.setInput((prev) => {
        const base = prev.trimEnd()
        if (!base) return trimmed
        return `${base} ${trimmed}`
      })
      window.requestAnimationFrame(() => {
        inputRef?.current?.focus()
        const el = inputRef?.current
        if (el) {
          const len = el.value.length
          el.setSelectionRange(len, len)
        }
      })
    },
    [chat.setInput, inputRef],
  )

  const voiceInput = useVoiceInput({
    enabled: visible && chat.status !== 'offline',
    disabled: chat.status === 'thinking' || chat.status === 'offline',
    onTranscript: appendToInput,
    onError: handleVoiceError,
  })

  const readAloud = useReadAloud(
    visible && chat.status !== 'offline',
    handleVoiceError,
  )

  const handleUserTranscript = useCallback(
    async (text: string) => {
      const reply = await chat.sendText(text)
      return reply?.text ?? null
    },
    [chat.sendText],
  )

  const legacyVoice = useVoiceDialog({
    enabled:
      visible &&
      chat.status !== 'offline' &&
      !REALTIME_VOICE_ENABLED,
    chatStatus: chat.status,
    onUserTranscript: handleUserTranscript,
    onVoiceError: handleVoiceError,
  })

  const realtimeVoice = useRealtimeVoice({
    enabled: visible && chat.status !== 'offline' && REALTIME_VOICE_ENABLED,
    sessionId,
    characterId: DEFAULT_CHARACTER_ID,
    onError: handleVoiceError,
  })

  const voiceActive = REALTIME_VOICE_ENABLED
    ? realtimeVoice.isConnected
    : legacyVoice.active

  const send = useCallback(async () => {
    const text = chat.input.trim()
    if (!text) return
    const reply = await chat.sendText(text)
    if (reply?.text && readAloud.on && !voiceActive) {
      await readAloud.speak(reply.text)
    }
  }, [chat.input, chat.sendText, readAloud.on, readAloud.speak, voiceActive])

  return {
    ...chat,
    send,
    voice: legacyVoice,
    realtimeVoice,
    realtimeVoiceEnabled: REALTIME_VOICE_ENABLED,
    readAloud,
    voiceInput,
  }
}
