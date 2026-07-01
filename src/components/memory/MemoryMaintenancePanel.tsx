import { useState } from 'react'
import { cn } from '../../lib/cn'

type MaintenanceResult = {
  summary: string
  raw: string
}

const ACTIONS = [
  {
    id: 'daily' as const,
    title: 'Daily Review',
    subtitle: '编号回填与注册表同步',
    desc: '为记忆文件补齐 ST/MT/LT 编号。',
  },
  {
    id: 'weekly' as const,
    title: 'Weekly Rollup',
    subtitle: '7 天短期 → 中期',
    desc: '优先汇总标记为重要的短期记忆。',
  },
  {
    id: 'monthly' as const,
    title: 'Monthly Archive',
    subtitle: '月底中期 → 长期',
    desc: '生成长期快照并写入向量库。',
  },
  {
    id: 'catchup' as const,
    title: 'Catch Up',
    subtitle: '补跑全部维护任务',
    desc: '依次执行日/周/月维护。',
  },
]

type MemoryMaintenancePanelProps = {
  onRun: (action: 'daily' | 'weekly' | 'monthly' | 'catchup') => Promise<MaintenanceResult>
  className?: string
}

export function MemoryMaintenancePanel({ onRun, className }: MemoryMaintenancePanelProps) {
  const [busy, setBusy] = useState<string | null>(null)
  const [result, setResult] = useState<MaintenanceResult | null>(null)
  const [showRaw, setShowRaw] = useState(false)

  const run = async (id: typeof ACTIONS[number]['id']) => {
    setBusy(id)
    try {
      const res = await onRun(id)
      setResult(res)
    } catch (err) {
      setResult({
        summary: err instanceof Error ? err.message : '维护失败',
        raw: '',
      })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div>
        <h3 className="text-sm font-medium text-jarvis-text">Memory Maintenance</h3>
        <p className="mt-1 text-xs text-jarvis-text-muted">
          分层管线：对话仅存短期 → 周期总结入中期 → 月底归档入长期。
        </p>
      </div>
      <div className="space-y-2">
        {ACTIONS.map((action) => (
          <button
            key={action.id}
            type="button"
            disabled={busy !== null}
            onClick={() => void run(action.id)}
            className={cn(
              'w-full rounded-jarvis-md border border-jarvis-border bg-jarvis-card p-3 text-left transition-colors',
              'hover:border-jarvis-border-strong disabled:opacity-50',
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-jarvis-text">{action.title}</span>
              {busy === action.id && (
                <span className="text-[10px] text-jarvis-text-muted">执行中…</span>
              )}
            </div>
            <p className="mt-0.5 text-[11px] text-jarvis-accent/90">{action.subtitle}</p>
            <p className="mt-1 text-xs text-jarvis-text-muted">{action.desc}</p>
          </button>
        ))}
      </div>
      {result && (
        <div className="rounded-jarvis-md border border-jarvis-border bg-jarvis-card p-3">
          <p className="text-xs text-jarvis-text">{result.summary}</p>
          {result.raw && (
            <>
              <button
                type="button"
                onClick={() => setShowRaw((v) => !v)}
                className="mt-2 text-[10px] text-jarvis-text-muted underline"
              >
                {showRaw ? '隐藏原始日志' : '查看原始日志'}
              </button>
              {showRaw && (
                <pre className="mt-2 max-h-40 overflow-auto text-[10px] text-jarvis-text-soft">
                  {result.raw}
                </pre>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

function summarizeMaintenanceResult(result: unknown): string {
  if (!result || typeof result !== 'object') return '维护已完成。'
  const r = result as Record<string, unknown>
  if (r.mode === 'tiered' && typeof r.backfill_ids === 'number') {
    return `编号回填完成，更新 ${r.backfill_ids} 条。`
  }
  if (r.rollup) return `Rollup：${String(r.rollup)}`
  if (r.week && r.rollup) return `周维护 ${r.week}：${String(r.rollup)}`
  if (r.month && r.rollup) return `月维护 ${r.month}：${String(r.rollup)}`
  if (r.daily || r.weekly || r.monthly) return '补跑任务已执行，请查看原始日志了解详情。'
  return '维护任务已完成。'
}

export function formatMaintenanceResponse(result: unknown): MaintenanceResult {
  return {
    summary: summarizeMaintenanceResult(result),
    raw: JSON.stringify(result, null, 2),
  }
}
