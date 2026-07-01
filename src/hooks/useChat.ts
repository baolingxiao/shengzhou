import { useCallback, useEffect, useRef, useState } from 'react'
import {
  type CharacterInfo,
  type ChatMessage,
  type ChatReply,
  checkBackendHealth,
  fetchCharacter,
  sendChatMessage,
} from '../lib/chatApi'
import { useUserSession } from '../contexts/UserSessionContext'
import { DEFAULT_CHARACTER_ID } from '../lib/characterConfig'
import { delayForSegment, sleep } from '../lib/replySegments'
import { trace } from '../lib/debugTrace'
import { beginTrace } from '../lib/executionTrace'
import { useMemoryTransparencyAttach } from './useMemoryTransparency'

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function useChat(enabled: boolean, onChatReply?: (reply: ChatReply) => void) {
  const { sessionId } = useUserSession()
  const { attachToLastAssistant } = useMemoryTransparencyAttach(sessionId)
  const [character, setCharacter] = useState<CharacterInfo | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<'offline' | 'ready' | 'thinking'>('offline')
  const [error, setError] = useState<string | null>(null)
  const bootstrapped = useRef(false)
  const bootSessionId = useRef(sessionId)

  useEffect(() => {
    if (bootSessionId.current !== sessionId) {
      bootSessionId.current = sessionId
      bootstrapped.current = false
      setMessages([])
      setError(null)
      setStatus('offline')
    }

    trace('chat.hook.enabled_change', { enabled, bootstrapped: bootstrapped.current, sessionId })
    if (!enabled) return

    void (async () => {
      const online = await checkBackendHealth()
      trace('chat.hook.health', { online })
      if (!online) {
        setStatus('offline')
        setError('对话服务未启动，请 ⌘Q 退出后重新打开「贾维斯.app」')
        return
      }
      if (bootstrapped.current) {
        setStatus((prev) => (prev === 'offline' ? 'ready' : prev))
        setError(null)
        return
      }
      bootstrapped.current = true

      try {
        const info = await fetchCharacter(DEFAULT_CHARACTER_ID)
        setCharacter(info)
        setStatus('ready')
        setError(null)
        trace('chat.hook.character_loaded', { name: info.name, sessionId })
      } catch (err) {
        setStatus('offline')
        setError(err instanceof Error ? err.message : '无法加载角色')
        trace('chat.hook.character_error', { error: String(err) }, 'alert')
      }
    })()
  }, [enabled, sessionId])

  const sendText = useCallback(async (rawText: string) => {
    const text = rawText.trim()
    if (!text || status === 'thinking') {
      trace('chat.send_skipped', { textLen: text.length, status })
      return null
    }

    trace('chat.send_start', { textPreview: text.slice(0, 40), status })
    const traceId = beginTrace(text)
    const userMsg: ChatMessage = { id: makeId(), role: 'user', text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setStatus('thinking')
    setError(null)

    try {
      const reply = await sendChatMessage(text, sessionId, DEFAULT_CHARACTER_ID, traceId)
      trace('chat.send_success', {
        replyLen: reply.text.length,
        route: reply.route,
        blocked: reply.blocked,
        trust_delta: reply.trust_delta,
        work_mode: reply.work_mode,
        segments: reply.segments?.length,
      })
      const parts =
        reply.segments && reply.segments.length > 0 ? reply.segments : [reply.text]
      const assistantIds: string[] = []
      for (let i = 0; i < parts.length; i += 1) {
        if (i > 0) {
          await sleep(delayForSegment(parts[i] ?? '', i))
        }
        const partText = parts[i] ?? ''
        const msgId = makeId()
        assistantIds.push(msgId)
        setMessages((prev) => [
          ...prev,
          { id: msgId, role: 'assistant', text: partText },
        ])
      }
      setStatus('ready')
      onChatReply?.(reply)
      const fullReply = parts.join('')
      void attachToLastAssistant(text, fullReply).then((memoryUsed) => {
        if (!memoryUsed) return
        const lastId = assistantIds[assistantIds.length - 1]
        if (!lastId) return
        setMessages((prev) =>
          prev.map((m) => (m.id === lastId ? { ...m, memoryUsed } : m)),
        )
      })
      return reply
    } catch (err) {
      trace('chat.send_error', { error: String(err) }, 'alert')
      setError(err instanceof Error ? err.message : '发送失败')
      setStatus('ready')
      return null
    }
  }, [status, sessionId, onChatReply, attachToLastAssistant])

  const send = useCallback(async () => {
    await sendText(input)
  }, [input, sendText])

  return {
    character,
    messages,
    input,
    setInput,
    send,
    sendText,
    status,
    error,
    setError,
  }
}
