import { motion, AnimatePresence } from 'motion/react'
import { cn } from '../../lib/cn'

type MemoryMessageActionSheetProps = {
  open: boolean
  onClose: () => void
  onDeleteOne: () => void
  onEnterSelection: () => void
}

/** 点击单条消息后弹出的操作菜单。 */
export function MemoryMessageActionSheet({
  open,
  onClose,
  onDeleteOne,
  onEnterSelection,
}: MemoryMessageActionSheetProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            aria-label="关闭菜单"
            className="fixed inset-0 z-[90] bg-black/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed bottom-0 left-0 right-0 z-[95] mx-auto max-w-lg rounded-t-2xl border border-white/15 bg-[#1a1d26] px-4 pb-8 pt-3 shadow-2xl"
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
          >
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-white/20" />
            <button
              type="button"
              onClick={() => {
                onDeleteOne()
                onClose()
              }}
              className="flex w-full items-center justify-center rounded-xl bg-red-500/15 px-4 py-3.5 text-sm text-red-300"
            >
              删除这条
            </button>
            <button
              type="button"
              onClick={() => {
                onEnterSelection()
                onClose()
              }}
              className={cn(
                'mt-2 flex w-full items-center justify-center rounded-xl',
                'border border-white/15 bg-white/5 px-4 py-3.5 text-sm text-foreground',
              )}
            >
              选择
            </button>
            <button
              type="button"
              onClick={onClose}
              className="mt-2 flex w-full items-center justify-center px-4 py-3 text-sm text-muted"
            >
              取消
            </button>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
