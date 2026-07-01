import { cn } from '../../lib/cn'
import type { ChatHistoryMessage } from '../../lib/adminApi'
import { DEFAULT_CHARACTER_NAME } from '../../lib/characterConfig'

type MemoryChatBubblesProps = {
  messages: ChatHistoryMessage[]
  characterName?: string
  className?: string
  emptyText?: string
  interactive?: boolean
  selectionMode?: boolean
  selectedIndices?: Set<number>
  onMessageClick?: (index: number) => void
}

function Avatar({
  label,
  side,
}: {
  label: string
  side: 'user' | 'assistant'
}) {
  return (
    <div
      className={cn(
        'flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-xs font-medium',
        side === 'user'
          ? 'bg-[#4a7c59] text-white'
          : 'bg-[#3d4250] text-white/90',
      )}
      aria-hidden
    >
      {label.slice(0, 1)}
    </div>
  )
}

function Bubble({
  role,
  content,
  selected,
  selectionMode,
}: {
  role: 'user' | 'assistant'
  content: string
  selected?: boolean
  selectionMode?: boolean
}) {
  const isUser = role === 'user'
  return (
    <div className="relative">
      {selectionMode && (
        <span
          className={cn(
            'absolute -top-1 z-10 flex h-5 w-5 items-center justify-center rounded-full border text-[10px]',
            isUser ? '-left-1' : '-right-1',
            selected
              ? 'border-jarvis-accent bg-jarvis-accent text-white'
              : 'border-jarvis-border bg-jarvis-card text-transparent',
          )}
        >
          ✓
        </span>
      )}
      <div
        className={cn(
          'relative max-w-[min(100%,16rem)] whitespace-pre-wrap break-words px-3 py-2 text-[13px] leading-relaxed transition ring-offset-1',
          isUser
            ? 'rounded-lg rounded-tr-sm bg-jarvis-accent/25 text-jarvis-text'
            : 'rounded-lg rounded-tl-sm bg-jarvis-card-strong text-jarvis-text shadow-sm',
          selectionMode && 'cursor-pointer',
          selected && 'ring-2 ring-jarvis-accent',
        )}
      >
        {content}
      </div>
    </div>
  )
}

/** 微信风格对话气泡：用户在右（绿），AI 在左（白）。 */
export function MemoryChatBubbles({
  messages,
  characterName = DEFAULT_CHARACTER_NAME,
  className,
  emptyText = '暂无对话内容',
  interactive = false,
  selectionMode = false,
  selectedIndices,
  onMessageClick,
}: MemoryChatBubblesProps) {
  if (messages.length === 0) {
    return <p className="py-6 text-center text-xs text-muted/70">{emptyText}</p>
  }

  return (
    <div
      className={cn(
        'space-y-3 rounded-jarvis-md bg-[#1c1c22] px-3 py-4',
        className,
      )}
    >
      {messages.map((msg, i) => {
        const isUser = msg.role === 'user'
        const selected = selectedIndices?.has(i) ?? false
        const clickable = interactive || selectionMode

        return (
          <div
            key={`${msg.role}-${i}`}
            className={cn('flex items-start gap-2', isUser ? 'flex-row-reverse' : 'flex-row')}
          >
            <Avatar label={isUser ? '你' : characterName} side={isUser ? 'user' : 'assistant'} />
            <button
              type="button"
              disabled={!clickable}
              onClick={() => clickable && onMessageClick?.(i)}
              className={cn(
                'text-left',
                clickable ? 'cursor-pointer' : 'cursor-default',
                'disabled:cursor-default',
              )}
            >
              <Bubble
                role={msg.role}
                content={msg.content}
                selected={selected}
                selectionMode={selectionMode}
              />
            </button>
          </div>
        )
      })}
    </div>
  )
}
