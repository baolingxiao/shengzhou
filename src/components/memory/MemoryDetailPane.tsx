import { ChatBubble } from '../chat/ChatBubble'
import { MemoryChatBubbles } from '../admin/MemoryChatBubbles'
import { parseMemoryChatBody } from '../../lib/parseMemoryChat'
import { cn } from '../../lib/cn'
import type { ChatHistoryMessage } from '../../lib/adminApi'

type MemoryDetailPaneProps = {
  memoryId?: string
  title?: string
  body?: string
  messages?: ChatHistoryMessage[]
  loading?: boolean
  emptyText?: string
  className?: string
  interactiveBubbles?: boolean
  selectionMode?: boolean
  selectedIndices?: Set<number>
  onMessageClick?: (index: number) => void
}

export function MemoryDetailPane({
  memoryId,
  title,
  body = '',
  messages,
  loading,
  emptyText = '选择一条记忆查看详情',
  className,
  interactiveBubbles,
  selectionMode,
  selectedIndices,
  onMessageClick,
}: MemoryDetailPaneProps) {
  const parsed = messages ?? (body ? parseMemoryChatBody(body) : [])

  return (
    <div className={cn('flex h-full min-h-0 flex-col', className)}>
      {memoryId && (
        <div className="shrink-0 border-b border-jarvis-border px-4 py-3">
          <p className="font-mono text-[11px] text-jarvis-accent">{memoryId}</p>
          <h3 className="mt-1 text-sm font-medium text-jarvis-text">{title || '记忆详情'}</h3>
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="space-y-3">
            <div className="h-4 w-2/3 animate-pulse rounded bg-jarvis-card-strong" />
            <div className="h-20 animate-pulse rounded-jarvis-md bg-jarvis-card" />
          </div>
        )}
        {!loading && !memoryId && !body && (
          <p className="py-12 text-center text-sm text-jarvis-text-muted">{emptyText}</p>
        )}
        {!loading && parsed.length > 0 && (
          <MemoryChatBubbles
            messages={parsed}
            className="rounded-jarvis-md border border-jarvis-border bg-[#1c1c22]"
            interactive={interactiveBubbles}
            selectionMode={selectionMode}
            selectedIndices={selectedIndices}
            onMessageClick={onMessageClick}
          />
        )}
        {!loading && parsed.length === 0 && body && (
          <div className="space-y-3">
            {body.split('\n\n').map((block, i) => (
              <ChatBubble key={i} role="system" density="compact" animate={false}>
                {block.trim()}
              </ChatBubble>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
