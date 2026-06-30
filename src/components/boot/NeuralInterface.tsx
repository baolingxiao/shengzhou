import { type KeyboardEvent, useCallback, useEffect, useRef } from 'react'
import { motion } from 'motion/react'
import { useChatWithVoice } from '../../hooks/useChatWithVoice'
import { useTrustPoints } from '../../hooks/useTrustPoints'
import { useWorkMode } from '../../hooks/useWorkMode'
import { useAdminRole } from '../../hooks/useAdminRole'
import { useUserSession } from '../../contexts/UserSessionContext'
import { trace } from '../../lib/debugTrace'
import { cn } from '../../lib/cn'
import { DEFAULT_CHARACTER_NAME } from '../../lib/characterConfig'
import { revealTransition } from '../../motion/springs'
import { IntimacyBar } from './IntimacyBar'
import { WorkModeBadge } from './WorkModeBadge'
import { Panel } from '../ui/Panel'

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
  const { username, isAdmin: sessionIsAdmin, sessionId } = useUserSession()
  const isAdmin = useAdminRole(username, sessionIsAdmin, visible)
  const {
    trust,
    saving: trustSaving,
    setTrustPoints,
    deltaFlash,
    applyFromChatReply,
  } = useTrustPoints(visible, isAdmin, username)
  const { snapshot: workMode, reload: reloadWorkMode } = useWorkMode(visible, sessionId)

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

  const statusLabel =
    readAloud.speaking
      ? '朗读中…'
      : realtimeVoiceEnabled && realtimeVoice.isConnected
        ? `Realtime · ${realtimeStatusLabel}`
        : status === 'thinking'
          ? '对方正在输入......'
          : voice.active && voice.statusHint
            ? voice.statusHint
            : status === 'offline'
              ? '服务离线'
              : character
                ? `${character.ai_type} · ${character.user_mbti}`
                : '就绪'

  return (
    <motion.div
      className={cn(
        'absolute inset-x-0 z-30 flex justify-center px-4 pb-6 md:pb-10',
        'top-[calc(20vh+min(36vmin,210px))] md:top-[calc(18vh+min(36vmin,210px))]',
        className,
      )}
      initial={{ opacity: 0, y: 24 }}
      animate={visible ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
      transition={revealTransition}
    >
      <div className="mx-4 flex w-full max-w-[calc(32rem+3rem)] items-stretch gap-2">
        <Panel
          glow
          gradient
          className="flex min-w-0 max-h-[min(72vh,560px)] flex-1 flex-col p-5 md:p-6"
        >
        <div className="mb-4 flex shrink-0 items-start justify-between gap-3">
          <div>
            <h1 className="text-lg font-medium tracking-tight text-white/95 [text-shadow:0_1px_12px_rgba(0,0,0,0.55)]">
              {character?.name ?? DEFAULT_CHARACTER_NAME}
            </h1>
            <p className="mt-0.5 text-sm text-white/80 [text-shadow:0_1px_10px_rgba(0,0,0,0.5)]">
              {statusLabel}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <WorkModeBadge snapshot={workMode} />
            <div className="flex items-center gap-2">
            {onLogout && (
              <button
                type="button"
                onClick={onLogout}
                className="rounded-full border border-white/25 px-2.5 py-1 text-xs text-white/75 transition-colors [text-shadow:0_1px_6px_rgba(0,0,0,0.4)] hover:border-white/40 hover:text-white/95"
              >
                退出
              </button>
            )}
            <StatusOrb active={status === 'thinking'} />
            </div>
          </div>
        </div>

        <div
          ref={scrollRef}
          className="mb-4 min-h-[120px] flex-1 space-y-3 overflow-y-auto pr-1"
          aria-live="polite"
        >
          {messages.length === 0 && status !== 'offline' && (
            <p className="text-sm text-white/72 [text-shadow:0_1px_10px_rgba(0,0,0,0.45)]">
              唤醒完成。向 {character?.name ?? '沈昼'} 说点什么吧。
            </p>
          )}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
                msg.role === 'user'
                  ? 'ml-auto bg-glow/15 text-foreground'
                  : 'mr-auto border border-border/80 bg-surface/85 text-foreground',
              )}
            >
              {msg.text}
            </div>
          ))}
        </div>

        {error && (
          <p className="mb-3 shrink-0 text-xs text-red-400/90" role="alert">
            {error}
          </p>
        )}

        <div className="shrink-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void readAloud.toggle()}
              disabled={status === 'offline' || readAloud.speaking}
              title={
                readAloud.available === false
                  ? readAloud.reason || '文字朗读不可用'
                  : undefined
              }
              className={cn(
                'rounded-full border px-3 py-1.5 text-xs transition-colors',
                readAloud.on
                  ? 'border-glow/50 bg-glow/15 text-glow'
                  : 'border-border/80 bg-surface/80 text-foreground/70 hover:text-foreground',
                'disabled:cursor-not-allowed disabled:opacity-40',
              )}
            >
              {readAloud.on ? '文字朗读：开' : '文字朗读：关'}
            </button>
            <button
              type="button"
              onClick={() => {
                if (realtimeVoiceEnabled) {
                  if (realtimeVoice.isConnected) {
                    realtimeVoice.stopRealtimeVoice()
                  } else {
                    void realtimeVoice.startRealtimeVoice()
                  }
                  return
                }
                void voice.toggle()
              }}
              disabled={
                status === 'offline' ||
                (!realtimeVoiceEnabled && voice.loading) ||
                status === 'thinking' ||
                realtimeVoice.status === 'connecting'
              }
              className={cn(
                'rounded-full border px-3 py-1.5 text-xs transition-colors',
                (realtimeVoiceEnabled ? realtimeVoice.isConnected : voice.active)
                  ? 'border-glow/50 bg-glow/15 text-glow'
                  : 'border-border/80 bg-surface/80 text-foreground/70 hover:text-foreground',
                'disabled:cursor-not-allowed disabled:opacity-40',
              )}
            >
              {realtimeVoiceEnabled
                ? realtimeVoice.status === 'connecting'
                  ? 'Connecting…'
                  : realtimeVoice.isConnected
                    ? 'Realtime 语音：开'
                    : 'Realtime 语音：关'
                : voice.loading
                  ? '语音启动中…'
                  : voice.active
                    ? '语音对话：开'
                    : '语音对话：关'}
            </button>
            {realtimeVoiceEnabled && realtimeVoice.isConnected && (
              <>
                <button
                  type="button"
                  onClick={() => realtimeVoice.interrupt()}
                  disabled={realtimeVoice.status !== 'speaking'}
                  className="rounded-full border border-border/80 bg-surface/80 px-3 py-1.5 text-xs text-foreground/70 transition-colors hover:text-foreground disabled:opacity-40"
                >
                  Interrupt
                </button>
                <button
                  type="button"
                  onClick={() => realtimeVoice.stopRealtimeVoice()}
                  className="rounded-full border border-red-400/40 bg-red-500/10 px-3 py-1.5 text-xs text-red-200 transition-colors hover:bg-red-500/20"
                >
                  Stop
                </button>
                <span className="text-xs text-muted/80">{realtimeStatusLabel}</span>
              </>
            )}
            {!realtimeVoiceEnabled && voice.active && (
              <span className="text-xs text-muted/80">{voice.voiceState}</span>
            )}
          </div>
          <label className="sr-only" htmlFor="neural-input">
            向沈昼发送消息
          </label>
          <div className="relative flex gap-2">
            <input
              ref={inputRef}
              id="neural-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={status === 'offline' || status === 'thinking' || voiceInput.transcribing}
              placeholder={
                status === 'offline'
                  ? '对话服务未启动，请重启贾维斯 App…'
                  : voiceInput.recording
                    ? '正在听…'
                    : voiceInput.transcribing
                      ? '识别中…'
                      : '说点什么…'
              }
              className={cn(
                'min-w-0 flex-1 rounded-2xl border border-border/90 bg-surface/90 px-4 py-3.5',
                'text-sm text-foreground placeholder:text-muted/80',
                'outline-none transition-shadow focus:shadow-[0_0_0_3px_rgba(0,90,167,0.22)]',
                'disabled:cursor-not-allowed disabled:opacity-60',
              )}
            />
            <button
              type="button"
              onClick={() => voiceInput.toggle()}
              disabled={
                status === 'offline' ||
                status === 'thinking' ||
                voiceInput.transcribing ||
                voiceInput.available === false
              }
              title={
                voiceInput.recording
                  ? '点击结束录音（文字填入输入框，需手动发送）'
                  : voiceInput.transcribing
                    ? '正在识别…'
                    : voiceInput.available === false
                      ? '语音输入不可用'
                      : '语音转文字填入输入框，按回车或点发送'
              }
              aria-label={voiceInput.recording ? '结束语音输入' : '语音输入'}
              className={cn(
                'flex h-[50px] w-[50px] shrink-0 items-center justify-center rounded-2xl border',
                'transition-colors disabled:cursor-not-allowed disabled:opacity-40',
                voiceInput.recording
                  ? 'border-red-400/60 bg-red-500/20 text-red-200'
                  : 'border-border/90 bg-surface/90 text-foreground/80 hover:border-glow/40 hover:text-glow',
              )}
            >
              <MicIcon active={voiceInput.recording} />
            </button>
            <button
              type="button"
              onClick={handleSend}
              disabled={
                !input.trim() ||
                status === 'offline' ||
                status === 'thinking' ||
                voiceInput.transcribing
              }
              className={cn(
                'shrink-0 rounded-2xl bg-glow px-4 py-3.5 text-sm font-medium text-white',
                'transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40',
              )}
            >
              发送
            </button>
          </div>
        </div>
        </Panel>

        <IntimacyBar
          trust={trust}
          editable={isAdmin}
          saving={trustSaving}
          deltaFlash={deltaFlash}
          onChange={(value) => void setTrustPoints(value)}
          className="max-h-[min(72vh,560px)]"
        />
      </div>
    </motion.div>
  )
}

function MicIcon({ active }: { active: boolean }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" />
      <path d="M19 11a7 7 0 0 1-14 0" />
      <path d="M12 18v3" />
      {active && (
        <circle cx="12" cy="12" r="9" className="animate-pulse opacity-30" fill="currentColor" stroke="none" />
      )}
    </svg>
  )
}

function StatusOrb({ active }: { active: boolean }) {
  return (
    <div className="relative flex h-10 w-10 items-center justify-center">
      <motion.span
        className="absolute inset-0 rounded-full bg-glow/25 blur-md"
        animate={
          active
            ? { scale: [0.9, 1.15, 0.9], opacity: [0.6, 1, 0.6] }
            : { scale: [0.95, 1.08, 0.95], opacity: [0.5, 0.8, 0.5] }
        }
        transition={{
          duration: active ? 1.2 : 3,
          repeat: Infinity,
          ease: [0.22, 1, 0.36, 1],
        }}
      />
      <span className="relative h-3 w-3 rounded-full bg-gradient-to-b from-glow-core to-glow shadow-[0_0_12px_rgba(0,90,167,0.45)]" />
    </div>
  )
}
