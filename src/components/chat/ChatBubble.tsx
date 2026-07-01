import type { ReactNode } from 'react'
import { motion } from 'motion/react'
import { cn } from '../../lib/cn'
import { jarvisMotion } from '../../lib/motion/jarvisMotion'

export type ChatBubbleRole = 'user' | 'assistant' | 'system'

type ChatBubbleProps = {
  role: ChatBubbleRole
  children: ReactNode
  density?: 'compact' | 'regular'
  metadata?: ReactNode
  className?: string
  animate?: boolean
}

/** 主聊天与记忆详情共用的 Apple Messages 风格气泡 */
export function ChatBubble({
  role,
  children,
  density = 'regular',
  metadata,
  className,
  animate = true,
}: ChatBubbleProps) {
  const isUser = role === 'user'
  const isSystem = role === 'system'
  const pad = density === 'compact' ? 'px-3 py-2 text-[13px]' : 'px-4 py-2.5 text-sm'

  const bubble = (
    <div className={cn('flex flex-col gap-1', isUser ? 'items-end' : 'items-start')}>
      <div
        className={cn(
          'max-w-[min(100%,28rem)] whitespace-pre-wrap break-words leading-relaxed',
          pad,
          isSystem
            ? 'rounded-jarvis-md border border-jarvis-border bg-jarvis-card text-jarvis-text-muted'
            : isUser
              ? 'rounded-jarvis-lg rounded-br-md bg-jarvis-blue text-white shadow-[0_8px_24px_-12px_rgba(0,113,227,0.55)]'
              : 'rounded-jarvis-lg rounded-bl-md border border-jarvis-border bg-jarvis-surface-dark text-jarvis-text backdrop-blur-[var(--blur-jarvis)]',
          className,
        )}
      >
        {children}
      </div>
      {metadata && <div className="px-1 text-[10px] text-jarvis-text-soft">{metadata}</div>}
    </div>
  )

  if (!animate) return bubble

  return (
    <motion.div
      initial={jarvisMotion.fadeUp.initial}
      animate={jarvisMotion.fadeUp.animate}
      transition={jarvisMotion.softSpring}
      className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}
    >
      {bubble}
    </motion.div>
  )
}
