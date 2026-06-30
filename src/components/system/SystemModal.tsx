import type { ReactNode } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Panel } from '../ui/Panel'
import { cn } from '../../lib/cn'

type SystemModalProps = {
  open: boolean
  title: string
  children: ReactNode
  className?: string
}

export function SystemModal({ open, title, children, className }: SystemModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="system-modal-title"
        >
          <div className="absolute inset-0 bg-black/55 backdrop-blur-sm" />
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            className={cn('relative w-full max-w-md', className)}
          >
            <Panel glow gradient className="p-6 shadow-2xl">
              <h2
                id="system-modal-title"
                className="text-lg font-medium tracking-tight text-white/95 [text-shadow:0_1px_10px_rgba(0,0,0,0.45)]"
              >
                {title}
              </h2>
              <div className="mt-4 space-y-4 text-sm text-white/85 [text-shadow:0_1px_8px_rgba(0,0,0,0.35)]">
                {children}
              </div>
            </Panel>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

type ModalActionsProps = {
  primaryLabel: string
  secondaryLabel?: string
  onPrimary: () => void
  onSecondary?: () => void
  primaryDisabled?: boolean
  primaryLoading?: boolean
}

export function ModalActions({
  primaryLabel,
  secondaryLabel = '稍后',
  onPrimary,
  onSecondary,
  primaryDisabled,
  primaryLoading,
}: ModalActionsProps) {
  return (
    <div className="flex flex-wrap justify-end gap-2 pt-2">
      {onSecondary && (
        <button
          type="button"
          onClick={onSecondary}
          className="rounded-full border border-white/30 px-4 py-2 text-sm text-white/80 transition hover:border-white/50 hover:text-white"
        >
          {secondaryLabel}
        </button>
      )}
      <button
        type="button"
        disabled={primaryDisabled || primaryLoading}
        onClick={onPrimary}
        className="rounded-full bg-white/90 px-4 py-2 text-sm font-medium text-[#1a1520] transition hover:bg-white disabled:opacity-50"
      >
        {primaryLoading ? '处理中…' : primaryLabel}
      </button>
    </div>
  )
}
