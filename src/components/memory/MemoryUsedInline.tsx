import { cn } from '../../lib/cn'

type MemoryUsedInlineProps = {
  memoryIds: string[]
  reasoning?: string
  onMemoryIdClick?: (memoryId: string) => void
  className?: string
}

export function MemoryUsedInline({
  memoryIds,
  reasoning,
  onMemoryIdClick,
  className,
}: MemoryUsedInlineProps) {
  if (memoryIds.length === 0) return null

  return (
    <div className={cn('mt-1.5 space-y-1', className)}>
      <div className="flex flex-wrap items-center gap-1">
        <span className="text-[10px] text-jarvis-text-soft">引用记忆</span>
        {memoryIds.map((id) => (
          <button
            key={id}
            type="button"
            onClick={() => onMemoryIdClick?.(id)}
            className={cn(
              'rounded-full border border-jarvis-accent/35 bg-jarvis-accent-soft/50',
              'px-2 py-0.5 font-mono text-[10px] text-jarvis-accent',
              onMemoryIdClick && 'hover:border-jarvis-accent/60',
            )}
          >
            {id}
          </button>
        ))}
      </div>
      {reasoning && (
        <p className="text-[10px] leading-relaxed text-jarvis-text-soft line-clamp-2">
          {reasoning}
        </p>
      )}
    </div>
  )
}
