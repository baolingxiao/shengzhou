import type { RefObject } from 'react'
import { ChatBubble } from './ChatBubble'
import { MemoryUsedInline } from '../memory/MemoryUsedInline'
import type { ChatMessage } from '../../lib/chatApi'

type MessageListProps = {
  messages: ChatMessage[]
  emptyHint?: string
  showEmpty?: boolean
  scrollRef?: RefObject<HTMLDivElement | null>
  className?: string
  onMemoryIdClick?: (memoryId: string) => void
}

export function MessageList({
  messages,
  emptyHint,
  showEmpty = true,
  scrollRef,
  className,
  onMemoryIdClick,
}: MessageListProps) {
  return (
    <div
      ref={scrollRef}
      className={className}
      aria-live="polite"
    >
      {showEmpty && messages.length === 0 && emptyHint && (
        <p className="py-8 text-center text-sm font-light tracking-[-0.01em] text-jarvis-text-muted">
          {emptyHint}
        </p>
      )}
      <div className="space-y-3">
        {messages.map((msg) => (
          <div key={msg.id}>
            <ChatBubble role={msg.role}>{msg.text}</ChatBubble>
            {msg.role === 'assistant' && msg.memoryUsed && (
              <MemoryUsedInline
                memoryIds={msg.memoryUsed.memoryIds}
                reasoning={msg.memoryUsed.reasoning}
                onMemoryIdClick={onMemoryIdClick}
                className="pl-1"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
