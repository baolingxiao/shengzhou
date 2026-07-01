import { useState } from 'react'
import type { KeyboardEvent, RefObject } from 'react'
import { motion } from 'motion/react'
import { cn } from '../../lib/cn'
import { jarvisTransition } from '../../lib/motion/jarvisMotion'
import { StatusOrb, type StatusOrbState } from '../system/StatusOrb'

type ChatComposerProps = {
  inputRef?: RefObject<HTMLInputElement | null>
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onKeyDown?: (event: KeyboardEvent<HTMLInputElement>) => void
  disabled?: boolean
  placeholder?: string
  orbState?: StatusOrbState
  voiceRecording?: boolean
  voiceTranscribing?: boolean
  voiceInputAvailable?: boolean
  onToggleVoiceInput?: () => void
  realtimeConnected?: boolean
  onStopRealtime?: () => void
  onInterruptRealtime?: () => void
  realtimeSpeaking?: boolean
}

/** Floating composer：温暖暗玻璃胶囊输入区 */
export function ChatComposer({
  inputRef,
  value,
  onChange,
  onSend,
  onKeyDown,
  disabled,
  placeholder = '慢慢说…',
  orbState = 'ready',
  voiceRecording,
  voiceTranscribing,
  voiceInputAvailable = true,
  onToggleVoiceInput,
  realtimeConnected,
  onStopRealtime,
  onInterruptRealtime,
  realtimeSpeaking,
}: ChatComposerProps) {
  const [focused, setFocused] = useState(false)
  const listening = voiceRecording || realtimeConnected
  const showStop = realtimeConnected && onStopRealtime

  return (
    <motion.div
      animate={{ scale: focused ? 1.005 : 1 }}
      transition={jarvisTransition.composerFocus}
      className={cn(
        'flex items-center gap-2 rounded-jarvis-xl border p-2 pl-3 backdrop-blur-[var(--blur-jarvis)]',
        'bg-[rgba(255,255,255,0.06)] transition-[border-color,box-shadow] duration-200',
        focused
          ? 'border-[rgba(245,215,161,0.42)] shadow-[0_0_0_4px_rgba(245,215,161,0.08)]'
          : 'border-[rgba(255,255,255,0.14)] shadow-[0_16px_48px_-20px_rgba(0,0,0,0.45)]',
      )}
    >
      <div className="flex shrink-0 items-center justify-center">
        {listening ? (
          <StatusOrb
            state={voiceRecording ? 'listening' : realtimeSpeaking ? 'speaking' : 'listening'}
            size="sm"
          />
        ) : (
          <StatusOrb state={orbState} size="sm" />
        )}
      </div>

      <label className="sr-only" htmlFor="neural-input">
        发送消息
      </label>
      <input
        ref={inputRef}
        id="neural-input"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        disabled={disabled}
        placeholder={
          voiceTranscribing
            ? '识别中…'
            : voiceRecording
              ? '我在听…'
              : placeholder
        }
        className={cn(
          'min-w-0 flex-1 bg-transparent py-2.5 text-sm text-jarvis-text placeholder:text-jarvis-text-soft',
          'outline-none disabled:cursor-not-allowed disabled:opacity-50',
        )}
      />

      {showStop && (
        <button
          type="button"
          onClick={onStopRealtime}
          className="shrink-0 rounded-full border border-jarvis-red/35 px-2.5 py-1 text-[10px] text-jarvis-red/90"
        >
          结束
        </button>
      )}
      {realtimeSpeaking && onInterruptRealtime && (
        <button
          type="button"
          onClick={onInterruptRealtime}
          className="shrink-0 rounded-full border border-jarvis-border px-2.5 py-1 text-[10px] text-jarvis-text-soft"
        >
          打断
        </button>
      )}

      {onToggleVoiceInput && (
        <button
          type="button"
          onClick={onToggleVoiceInput}
          disabled={disabled || voiceTranscribing || voiceInputAvailable === false}
          aria-label={voiceRecording ? '结束语音输入' : '语音输入'}
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition-colors',
            voiceRecording
              ? 'border-jarvis-red/40 bg-jarvis-red/10 text-jarvis-red'
              : 'border-jarvis-border text-jarvis-text-soft hover:border-jarvis-border-strong hover:text-jarvis-text-muted',
            'disabled:cursor-not-allowed disabled:opacity-40',
          )}
        >
          <MicIcon active={!!voiceRecording} />
        </button>
      )}

      <button
        type="button"
        onClick={onSend}
        disabled={disabled || !value.trim()}
        aria-label="发送"
        className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
          'bg-[rgba(245,238,222,0.92)] text-[#1a1814] transition-opacity hover:opacity-90',
          'disabled:cursor-not-allowed disabled:opacity-35',
        )}
      >
        <span className="text-base leading-none">↑</span>
      </button>
    </motion.div>
  )
}

function MicIcon({ active }: { active: boolean }) {
  return (
    <svg
      width="18"
      height="18"
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
        <circle cx="12" cy="12" r="9" className="animate-pulse opacity-20" fill="currentColor" stroke="none" />
      )}
    </svg>
  )
}
