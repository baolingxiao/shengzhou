import { MemoryCard } from './MemoryCard'
import { cn } from '../../lib/cn'
import { shortMemorySessionLabel } from '../../lib/parseMemoryChat'
import type { MemoryItem } from '../../lib/adminApi'

type MemoryListProps = {
  items: MemoryItem[]
  selectedId?: string
  shortLabels?: boolean
  emptyText?: string
  onSelect: (item: MemoryItem) => void
  onMark?: (item: MemoryItem) => void
  onDelete?: (item: MemoryItem) => void
  className?: string
}

export function MemoryList({
  items,
  selectedId,
  shortLabels,
  emptyText = '暂无记忆条目',
  onSelect,
  onMark,
  onDelete,
  className,
}: MemoryListProps) {
  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-jarvis-text-muted">{emptyText}</p>
  }

  return (
    <ul className={cn('space-y-2', className)}>
      {items.map((item) => (
        <li key={item.id}>
          <MemoryCard
            item={
              shortLabels
                ? { ...item, title: shortMemorySessionLabel(item) }
                : item
            }
            selected={selectedId === item.id}
            compact
            onClick={() => onSelect(item)}
            onMark={onMark ? () => onMark(item) : undefined}
            onDelete={onDelete ? () => onDelete(item) : undefined}
          />
        </li>
      ))}
    </ul>
  )
}
