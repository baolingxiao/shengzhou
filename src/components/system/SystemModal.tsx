import type { ReactNode } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Panel } from '../ui/Panel'
import { cn } from '../../lib/cn'
import { jarvisMotion } from '../../lib/motion/jarvisMotion'

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
          transition={{ duration: 0.28 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="system-modal-title"
        >
          <div className="absolute inset-0 bg-[rgba(8,10,14,0.62)] backdrop-blur-md" />
          <motion.div
            initial={jarvisMotion.scaleIn.initial}
            animate={jarvisMotion.scaleIn.animate}
            exit={jarvisMotion.scaleIn.exit}
            transition={jarvisMotion.softSpring}
            className={cn('relative w-full max-w-md', className)}
          >
            <Panel jarvis glow className="p-6 shadow-[0_32px_100px_rgba(0,0,0,0.45)]">
              <h2
                id="system-modal-title"
                className="text-lg font-normal tracking-[-0.02em] text-jarvis-text"
              >
                {title}
              </h2>
              <div className="mt-4 space-y-4 text-sm leading-relaxed text-jarvis-text-muted">
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
          className="rounded-full border border-jarvis-border px-4 py-2 text-sm text-jarvis-text-muted transition hover:border-jarvis-border-strong hover:text-jarvis-text"
        >
          {secondaryLabel}
        </button>
      )}
      <button
        type="button"
        disabled={primaryDisabled || primaryLoading}
        onClick={onPrimary}
        className="rounded-full bg-[rgba(245,238,222,0.92)] px-4 py-2 text-sm font-medium text-[#1a1814] transition hover:opacity-90 disabled:opacity-50"
      >
        {primaryLoading ? '处理中…' : primaryLabel}
      </button>
    </div>
  )
}
