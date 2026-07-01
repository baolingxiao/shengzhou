import { type KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { useChatWithVoice } from '../../hooks/useChatWithVoice'
import { useTrustPoints } from '../../hooks/useTrustPoints'
import { useWorkMode } from '../../hooks/useWorkMode'
import { useAdminRole } from '../../hooks/useAdminRole'
import { useUserSession } from '../../contexts/UserSessionContext'
import { trace } from '../../lib/debugTrace'
import { cn } from '../../lib/cn'
import { DEFAULT_CHARACTER_NAME } from '../../lib/characterConfig'
import { companionEmptyHint, jarvisMotion } from '../../lib/motion/jarvisMotion'
import { IntimacyBar } from './IntimacyBar'
import { MemoryPeekPanel } from '../memory/MemoryPeekPanel'
import { WorkModeBadge } from './WorkModeBadge'
import { Panel } from '../ui/Panel'
import { ConversationHeader } from '../chat/ConversationHeader'
import { MessageList } from '../chat/MessageList'
import { ChatComposer } from '../chat/ChatComposer'
import { ConversationModeMenu } from '../chat/ConversationModeMenu'
import type { StatusOrbState } from '../system/StatusOrb'

type NeuralInterfaceProps = {
  visible: boolean
  onLogout?: () => void
  className?: string
}

export function NeuralInterface({
  visible,
  onLogout,
  className,
}: NeuralInterfaceProps) {
  const { username, role, isAdmin: sessionIsAdmin, sessionId } = useUserSession()
  const isDeveloper = role === 'developer'
  const isAdmin = useAdminRole(username, sessionIsAdmin, visible)
  const {
    trust,
    saving: trustSaving,
    setTrustPoints,
    deltaFlash,
    applyFromChatReply,
  } = useTrustPoints(visible && isDeveloper, isAdmin, username)
  const { snapshot: workMode, reload: reloadWorkMode } = useWorkMode(visible && isDeveloper, sessionId)

  const handleChatReply = useCallback(
    (reply: import('../../lib/chatApi').ChatReply) => {
      applyFromChatReply(reply)
      void reloadWorkMode()
    },
    [applyFromChatReply, reloadWorkMode],
  )

  const inputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const prevVisible = useRef(visible)
  const [peekMemoryId, setPeekMemoryId] = useState<string | null>(null)

  const {
    character,
    messages,
    input,
    setInput,
    send,
    status,
    error,
    voice,
    realtimeVoice,
    realtimeVoiceEnabled,
    readAloud,
    voiceInput,
  } = useChatWithVoice(visible, handleChatReply, inputRef)

  useEffect(() => {
    trace('chat.interface.mount')
    return () => trace('chat.interface.unmount', {}, 'warn')
  }, [])

  useEffect(() => {
    if (prevVisible.current !== visible) {
      trace('chat.interface.visible', { from: prevVisible.current, to: visible })
      prevVisible.current = visible
    }
  }, [visible])

  useEffect(() => {
    if (!visible || !scrollRef.current) return
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages, visible])

  const handleSend = () => {
    trace('chat.send_click', { inputLen: input.trim().length, status })
    void send()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter') return
    trace('chat.enter_key', {
      isComposing: event.nativeEvent.isComposing,
      inputLen: input.trim().length,
      status,
    })
    if (event.nativeEvent.isComposing) {
      event.preventDefault()
      return
    }
    event.preventDefault()
    handleSend()
  }

  const realtimeStatusLabel = (() => {
    switch (realtimeVoice.status) {
      case 'connecting':
        return 'Connecting…'
      case 'connected':
      case 'listening':
        return 'Listening'
      case 'speaking':
        return 'Speaking'
      case 'error':
        return 'Error'
      default:
        return ''
    }
  })()

  const orbState: StatusOrbState = (() => {
    if (status === 'offline') return 'offline'
    if (readAloud.speaking || realtimeVoice.status === 'speaking') return 'speaking'
    if (status === 'thinking') return 'thinking'
    if (voiceInput.recording || (realtimeVoiceEnabled && realtimeVoice.isConnected)) return 'listening'
    return 'ready'
  })()

  const statusLabel = (() => {
    if (status === 'offline') return 'Offline'
    if (readAloud.speaking) return 'Speaking'
    if (realtimeVoiceEnabled && realtimeVoice.isConnected) return `Realtime · ${realtimeStatusLabel || 'Listening'}`
    if (status === 'thinking') return 'Thinking'
    if (voiceInput.recording) return 'Listening'
    if (voiceInput.transcribing) return 'Transcribing'
    if (voice.active && voice.statusHint) return voice.statusHint
    return 'Ready'
  })()

  const composerDisabled =
    status === 'offline' || status === 'thinking' || voiceInput.transcribing

  return (
    <motion.div
      className={cn(
        'absolute inset-x-0 z-30 flex justify-center px-4 pb-5 md:pb-8',
        'top-[calc(18vh+min(32vmin,200px))] md:top-[calc(16vh+min(32vmin,200px))]',
        className,
      )}
      initial={jarvisMotion.fadeUp.initial}
      animate={visible ? jarvisMotion.fadeUp.animate : jarvisMotion.fadeUp.exit}
      transition={jarvisMotion.softSpring}
    >
      <div className="flex w-full max-w-[720px] items-stretch gap-3">
        <Panel
          jarvis
          glow
          className="flex min-h-0 min-w-0 max-h-[min(76vh,640px)] flex-1 flex-col p-4 md:p-5"
        >
          <ConversationHeader
            name={character?.name ?? DEFAULT_CHARACTER_NAME}
            statusLabel={statusLabel}
            orbState={orbState}
            onLogout={onLogout}
            trailing={isDeveloper ? <WorkModeBadge snapshot={workMode} /> : undefined}
          />

          <MessageList
            scrollRef={scrollRef}
            messages={messages}
            showEmpty={status !== 'offline'}
            emptyHint={companionEmptyHint()}
            className="mb-3 min-h-[120px] flex-1 overflow-y-auto pr-1"
            onMemoryIdClick={isDeveloper ? (id) => setPeekMemoryId(id) : undefined}
          />

          {error && (
            <p className="mb-2 shrink-0 text-xs text-jarvis-red" role="alert">
              {error}
            </p>
          )}

          <div className="shrink-0">
            <ConversationModeMenu
              disabled={status === 'offline'}
              readAloudOn={readAloud.on}
              readAloudAvailable={readAloud.available ?? true}
              readAloudReason={readAloud.reason}
              onToggleReadAloud={() => void readAloud.toggle()}
              realtimeEnabled={realtimeVoiceEnabled}
              realtimeConnected={realtimeVoice.isConnected}
              realtimeStatus={realtimeStatusLabel}
              onToggleRealtime={() => {
                if (realtimeVoice.isConnected) {
                  realtimeVoice.stopRealtimeVoice()
                } else {
                  void realtimeVoice.startRealtimeVoice()
                }
              }}
              voiceActive={voice.active}
              voiceLoading={voice.loading}
              onToggleLegacyVoice={() => void voice.toggle()}
            />

            <ChatComposer
              inputRef={inputRef}
              value={input}
              onChange={setInput}
              onSend={handleSend}
              onKeyDown={handleKeyDown}
              disabled={composerDisabled}
              placeholder={
                status === 'offline'
                  ? '对话服务未启动，请重启贾维斯 App…'
                  : '慢慢说…'
              }
              orbState={orbState}
              voiceRecording={voiceInput.recording}
              voiceTranscribing={voiceInput.transcribing}
              voiceInputAvailable={voiceInput.available !== false}
              onToggleVoiceInput={() => voiceInput.toggle()}
              realtimeConnected={realtimeVoiceEnabled && realtimeVoice.isConnected}
              realtimeSpeaking={realtimeVoice.status === 'speaking'}
              onStopRealtime={
                realtimeVoiceEnabled && realtimeVoice.isConnected
                  ? () => realtimeVoice.stopRealtimeVoice()
                  : undefined
              }
              onInterruptRealtime={
                realtimeVoiceEnabled && realtimeVoice.status === 'speaking'
                  ? () => realtimeVoice.interrupt()
                  : undefined
              }
            />
          </div>
        </Panel>

        {isDeveloper && (
          <IntimacyBar
            trust={trust}
            editable={isAdmin}
            saving={trustSaving}
            deltaFlash={deltaFlash}
            onChange={(value) => void setTrustPoints(value)}
            className="hidden max-h-[min(76vh,640px)] lg:flex"
          />
        )}
      </div>

      {isDeveloper && (
        <MemoryPeekPanel memoryId={peekMemoryId} onClose={() => setPeekMemoryId(null)} />
      )}
    </motion.div>
  )
}
