import { cn } from '../../lib/cn'
import type { MemoryTransparencyRecord } from '../../lib/adminApi'

type MemoryTransparencyListProps = {
  records: MemoryTransparencyRecord[]
  onMemoryIdClick: (memoryId: string) => void
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ts
  }
}

/** 每轮对话的记忆选号透明化列表。 */
export function MemoryTransparencyList({ records, onMemoryIdClick }: MemoryTransparencyListProps) {
  if (records.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-jarvis-text-muted">
        暂无记录。与沈昼对话后，这里会显示每轮选中的记忆编号。
      </p>
    )
  }

  return (
    <ul className="space-y-3">
      {records.map((row, i) => (
        <li
          key={`${row.ts}-${i}`}
          className="rounded-jarvis-md border border-jarvis-border bg-jarvis-card p-3"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] text-jarvis-text-soft">{formatTime(row.ts)}</span>
            <span className="text-[10px] text-jarvis-text-muted">
              {row.gate === 'identity' ? '身份/偏好检索' : '常规检索'}
              {row.vector_used ? ' · 向量' : ''}
            </span>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-jarvis-text">
            <span className="text-jarvis-text-muted">你：</span>
            {row.user_query}
          </p>
          {row.reply_preview && (
            <p className="mt-1 text-xs leading-relaxed text-jarvis-text-muted">
              <span className="text-jarvis-text-soft">沈昼：</span>
              {row.reply_preview}
              {row.reply_preview.length >= 240 ? '…' : ''}
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-1.5">
            {row.memory_ids.length === 0 ? (
              <span className="rounded-full bg-jarvis-card-strong px-2 py-0.5 text-[10px] text-jarvis-text-muted">
                未选中记忆编号
              </span>
            ) : (
              row.memory_ids.map((id) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => onMemoryIdClick(id)}
                  className={cn(
                    'rounded-full border border-jarvis-accent/40 bg-jarvis-accent-soft',
                    'px-2 py-0.5 font-mono text-[10px] text-jarvis-accent hover:border-jarvis-accent/60',
                  )}
                >
                  {id}
                </button>
              ))
            )}
          </div>
          {row.reasoning && (
            <p className="mt-2 text-[10px] leading-relaxed text-jarvis-text-soft">
              选号理由：{row.reasoning}
            </p>
          )}
        </li>
      ))}
    </ul>
  )
}
