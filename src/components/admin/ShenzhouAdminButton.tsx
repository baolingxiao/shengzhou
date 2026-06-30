import { useState } from 'react'
import { useUserSession } from '../../contexts/UserSessionContext'
import { cn } from '../../lib/cn'
import { ShenzhouAdminPanel } from './ShenzhouAdminPanel'

type ShenzhouAdminButtonProps = {
  className?: string
  visible?: boolean
}

/** 右下角入口：沈昼记忆与聊天记录后台 */
export function ShenzhouAdminButton({ className, visible = true }: ShenzhouAdminButtonProps) {
  const [open, setOpen] = useState(false)
  const { sessionId } = useUserSession()

  if (!visible) return null

  return (
    <>
      <button
        type="button"
        aria-label="沈昼记忆宫殿"
        title="沈昼记忆宫殿"
        onClick={() => setOpen(true)}
        className={cn(
          'fixed bottom-24 right-5 z-50 flex h-11 items-center gap-2 rounded-full',
          'border border-white/20 bg-[#12141a]/90 px-4 text-sm text-foreground/90',
          'shadow-lg backdrop-blur-md transition hover:border-white/35 hover:bg-[#1a1d26]',
          className,
        )}
      >
        <span className="text-base opacity-80" aria-hidden>
          ◇
        </span>
        记忆
      </button>
      <ShenzhouAdminPanel open={open} onClose={() => setOpen(false)} sessionId={sessionId} />
    </>
  )
}
