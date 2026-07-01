import { cn } from '../../lib/cn'
import type { MemoryFilterState } from '../../lib/memoryFilters'

type MemoryFiltersProps = {
  value: MemoryFilterState
  onChange: (next: MemoryFilterState) => void
  className?: string
}

export function MemoryFilters({ value, onChange, className }: MemoryFiltersProps) {
  return (
    <div className={cn('space-y-2', className)}>
      <input
        type="search"
        value={value.query}
        onChange={(e) => onChange({ ...value, query: e.target.value })}
        placeholder="搜索编号、关键词…"
        className={cn(
          'w-full rounded-jarvis-sm border border-jarvis-border bg-jarvis-card px-3 py-2',
          'text-xs text-jarvis-text placeholder:text-jarvis-text-soft outline-none',
          'focus:border-jarvis-border-strong',
        )}
      />
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onChange({ ...value, markedOnly: !value.markedOnly })}
          className={cn(
            'rounded-full border px-2.5 py-1 text-[10px] transition-colors',
            value.markedOnly
              ? 'border-jarvis-accent/50 bg-jarvis-accent-soft text-jarvis-accent'
              : 'border-jarvis-border text-jarvis-text-muted hover:text-jarvis-text',
          )}
        >
          ★ 仅重要
        </button>
        <select
          value={value.sort}
          onChange={(e) =>
            onChange({ ...value, sort: e.target.value as MemoryFilterState['sort'] })
          }
          className="rounded-full border border-jarvis-border bg-jarvis-card px-2 py-1 text-[10px] text-jarvis-text-muted outline-none"
        >
          <option value="date_desc">最新优先</option>
          <option value="date_asc">最早优先</option>
        </select>
      </div>
    </div>
  )
}
