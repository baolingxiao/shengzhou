import { motion, AnimatePresence } from 'motion/react'
import { cn } from '../../lib/cn'
import type { ChatHistoryMessage } from '../../lib/adminApi'
import { parseMemoryChatBody } from '../../lib/parseMemoryChat'
import { MemoryChatBubbles } from './MemoryChatBubbles'

type MemoryDetailSheetProps = {
  open: boolean
  memoryId?: string
  title?: string
  body?: string
  loading?: boolean
  onClose: () => void
}

/** 记忆详情：对话型用气泡，摘要型用正文。 */
export function MemoryDetailSheet({
  open,
  memoryId,
  title,
  body = '',
  loading,
  onClose,
}: MemoryDetailSheetProps) {
  const messages: ChatHistoryMessage[] = body ? parseMemoryChatBody(body) : []

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            aria-label="关闭详情"
            className="fixed inset-0 z-[85] bg-black/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className={cn(
              'fixed bottom-0 left-0 right-0 z-[90] mx-auto max-h-[min(75vh,560px)] w-full max-w-lg',
              'overflow-hidden rounded-t-2xl border border-white/15 bg-[#1a1d26] shadow-2xl',
            )}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
          >
            <div className="border-b border-white/10 px-4 py-3">
              <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-white/20" />
              {memoryId && (
                <p className="font-mono text-[11px] text-[#07c160]/90">{memoryId}</p>
              )}
              <h3 className="mt-1 text-sm font-medium text-foreground">{title || '记忆详情'}</h3>
            </div>
            <div className="max-h-[calc(min(75vh,560px)-4.5rem)] overflow-y-auto px-3 py-3">
              {loading && <p className="text-sm text-muted">加载中…</p>}
              {!loading && messages.length > 0 && (
                <MemoryChatBubbles messages={messages} className="rounded-xl" />
              )}
              {!loading && messages.length === 0 && body && (
                <pre className="whitespace-pre-wrap rounded-xl bg-[#ededed]/10 p-3 text-xs leading-relaxed text-foreground/90">
                  {body}
                </pre>
              )}
              {!loading && !body && (
                <p className="py-8 text-center text-sm text-muted">暂无内容</p>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
