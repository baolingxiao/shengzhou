import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { cn } from '../../lib/cn'
import { jarvisMotion } from '../../lib/motion/jarvisMotion'

type ConversationModeMenuProps = {
  readAloudOn: boolean
  readAloudAvailable: boolean
  readAloudReason?: string
  onToggleReadAloud: () => void
  realtimeEnabled: boolean
  realtimeConnected: boolean
  realtimeStatus: string
  onToggleRealtime: () => void
  voiceActive: boolean
  voiceLoading: boolean
  onToggleLegacyVoice: () => void
  disabled?: boolean
}

/** 轻量胶囊：收纳朗读 / 语音 / Realtime */
export function ConversationModeMenu({
  readAloudOn,
  readAloudAvailable,
  readAloudReason,
  onToggleReadAloud,
  realtimeEnabled,
  realtimeConnected,
  realtimeStatus,
  onToggleRealtime,
  voiceActive,
  voiceLoading,
  onToggleLegacyVoice,
  disabled,
}: ConversationModeMenuProps) {
  const [open, setOpen] = useState(false)

  const activeCount =
    (readAloudOn ? 1 : 0) +
    (realtimeEnabled ? (realtimeConnected ? 1 : 0) : voiceActive ? 1 : 0)

  return (
    <div className="relative mb-2.5">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] transition-colors',
          'border-jarvis-border/80 bg-jarvis-card/40 text-jarvis-text-soft',
          'hover:border-jarvis-border-strong hover:bg-jarvis-card-warm hover:text-jarvis-text-muted',
          'disabled:opacity-40',
          activeCount > 0 && 'border-jarvis-accent/35 bg-jarvis-accent-soft/60 text-jarvis-accent/90',
        )}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-jarvis-accent/80" />
        对话模式
        {activeCount > 0 && (
          <span className="rounded-full bg-jarvis-card-strong/80 px-1.5 py-0.5 text-[10px] tabular-nums">
            {activeCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={jarvisMotion.scaleIn.initial}
            animate={jarvisMotion.scaleIn.animate}
            exit={jarvisMotion.scaleIn.exit}
            transition={jarvisMotion.softSpring}
            className={cn(
              'absolute bottom-full left-0 z-20 mb-2 min-w-[220px] overflow-hidden',
              'rounded-jarvis-md border border-jarvis-border bg-jarvis-bg-soft/95 p-2',
              'shadow-[0_24px_64px_rgba(0,0,0,0.4)] backdrop-blur-[var(--blur-jarvis)]',
            )}
          >
            <ModeRow
              label="文字朗读"
              hint={readAloudAvailable === false ? readAloudReason : readAloudOn ? '开' : '关'}
              active={readAloudOn}
              disabled={disabled || readAloudAvailable === false}
              onClick={() => {
                onToggleReadAloud()
              }}
            />
            {realtimeEnabled ? (
              <ModeRow
                label="Realtime 语音"
                hint={realtimeConnected ? realtimeStatus || '已连接' : '关'}
                active={realtimeConnected}
                disabled={disabled}
                onClick={onToggleRealtime}
              />
            ) : (
              <ModeRow
                label="语音对话"
                hint={voiceLoading ? '启动中…' : voiceActive ? '开' : '关'}
                active={voiceActive}
                disabled={disabled || voiceLoading}
                onClick={onToggleLegacyVoice}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ModeRow({
  label,
  hint,
  active,
  disabled,
  onClick,
}: {
  label: string
  hint?: string
  active: boolean
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'flex w-full items-center justify-between rounded-jarvis-sm px-3 py-2 text-left text-xs transition-colors',
        active ? 'bg-jarvis-accent-soft text-jarvis-accent' : 'text-jarvis-text-muted hover:bg-jarvis-card',
        disabled && 'cursor-not-allowed opacity-40',
      )}
    >
      <span>{label}</span>
      <span className="text-[10px] opacity-80">{hint}</span>
    </button>
  )
}
