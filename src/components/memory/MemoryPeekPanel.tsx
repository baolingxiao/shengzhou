import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { fetchMemoryById } from '../../lib/adminApi'
import { cn } from '../../lib/cn'
import { MemoryDetailPane } from './MemoryDetailPane'

type MemoryPeekPanelProps = {
  memoryId: string | null
  onClose: () => void
  className?: string
}

export function MemoryPeekPanel({ memoryId, onClose, className }: MemoryPeekPanelProps) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!memoryId) return
    let cancelled = false
    setLoading(true)
    void fetchMemoryById(memoryId)
      .then((res) => {
        if (cancelled) return
        setTitle(res.title)
        setBody(res.body)
      })
      .catch(() => {
        if (!cancelled) setBody('读取失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [memoryId])

  return (
    <AnimatePresence>
      {memoryId && (
        <>
          <motion.button
            type="button"
            aria-label="关闭记忆预览"
            className="fixed inset-0 z-[60] bg-black/40 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className={cn(
              'fixed bottom-0 left-0 right-0 z-[65] max-h-[70vh] rounded-t-jarvis-lg',
              'border border-jarvis-border bg-jarvis-bg shadow-2xl',
              'lg:bottom-auto lg:left-auto lg:right-4 lg:top-24 lg:max-h-[min(520px,70vh)] lg:w-[360px] lg:rounded-jarvis-lg',
              className,
            )}
            initial={{ y: '100%', opacity: 0.9 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
          >
            <div className="flex items-center justify-between border-b border-jarvis-border px-4 py-2">
              <span className="text-xs text-jarvis-text-muted">记忆预览</span>
              <button
                type="button"
                onClick={onClose}
                className="text-xs text-jarvis-accent"
              >
                关闭
              </button>
            </div>
            <MemoryDetailPane
              memoryId={memoryId}
              title={title}
              body={body}
              loading={loading}
              className="max-h-[calc(70vh-40px)] lg:max-h-[calc(520px-40px)]"
            />
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
