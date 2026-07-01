import { cn } from '../../lib/cn'
import type { MemoryItem } from '../../lib/adminApi'

type MemoryCardProps = {
  item: MemoryItem
  selected?: boolean
  compact?: boolean
  onClick?: () => void
  onMark?: () => void
  onDelete?: () => void
}

export function MemoryCard({
  item,
  selected,
  compact,
  onClick,
  onMark,
  onDelete,
}: MemoryCardProps) {
  return (
    <article
      className={cn(
        'rounded-jarvis-md border transition-colors',
        selected
          ? 'border-jarvis-accent/45 bg-jarvis-accent-soft/40'
          : 'border-jarvis-border bg-jarvis-card hover:border-jarvis-border-strong',
        compact ? 'p-2.5' : 'p-3',
      )}
    >
      <button type="button" className="w-full text-left" onClick={onClick}>
        <p className="font-mono text-[10px] text-jarvis-accent">{item.memory_id}</p>
        <p className="mt-1 text-sm font-medium text-jarvis-text">
          {item.marked && <span className="text-jarvis-accent">★ </span>}
          {item.title}
        </p>
        {!compact && (
          <p className="mt-1 line-clamp-2 text-xs text-jarvis-text-muted">{item.preview}</p>
        )}
        <p className="mt-1 text-[10px] text-jarvis-text-soft">{item.category}</p>
      </button>
      {(onMark || onDelete) && (
        <div className="mt-2 flex gap-2">
          {onMark && (
            <button
              type="button"
              onClick={onMark}
              className="text-[11px] text-jarvis-text-muted hover:text-jarvis-text"
            >
              {item.marked ? '取消标记' : '标记重要'}
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              onClick={onDelete}
              className="text-[11px] text-jarvis-red/90 hover:text-jarvis-red"
            >
              删除
            </button>
          )}
        </div>
      )}
    </article>
  )
}
