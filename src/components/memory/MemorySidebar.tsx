import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export type MemoryTabId = 'short' | 'medium' | 'long' | 'transparency' | 'maintain'

export const MEMORY_TABS: { id: MemoryTabId; label: string; sub: string }[] = [
  { id: 'short', label: '当前', sub: 'Short' },
  { id: 'medium', label: '周期', sub: 'Mid' },
  { id: 'long', label: '长期', sub: 'Long' },
  { id: 'transparency', label: '引用', sub: 'Retrieval' },
  { id: 'maintain', label: '维护', sub: 'Maint' },
]

type MemorySidebarProps = {
  tab: MemoryTabId
  onTabChange: (tab: MemoryTabId) => void
  counts: Record<string, number>
  filters?: ReactNode
  className?: string
}

export function MemorySidebar({
  tab,
  onTabChange,
  counts,
  filters,
  className,
}: MemorySidebarProps) {
  return (
    <aside className={cn('flex min-h-0 flex-col border-jarvis-border lg:border-r', className)}>
      <div className="shrink-0 p-3">
        <p className="text-[10px] uppercase tracking-[0.14em] text-jarvis-text-soft">Memory Space</p>
        <p className="mt-1 text-xs text-jarvis-text-muted">
          ST {counts.short ?? 0} · MT {counts.medium ?? 0} · LT {counts.long ?? 0}
        </p>
      </div>
      <nav className="shrink-0 space-y-1 px-2">
        {MEMORY_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onTabChange(t.id)}
            className={cn(
              'flex w-full items-center justify-between rounded-jarvis-sm px-3 py-2 text-left text-xs transition-colors',
              tab === t.id
                ? 'bg-jarvis-accent-soft text-jarvis-accent'
                : 'text-jarvis-text-muted hover:bg-jarvis-card hover:text-jarvis-text',
            )}
          >
            <span>{t.label}</span>
            <span className="text-[10px] opacity-60">{t.sub}</span>
          </button>
        ))}
      </nav>
      {filters && <div className="mt-3 shrink-0 border-t border-jarvis-border p-3">{filters}</div>}
    </aside>
  )
}
