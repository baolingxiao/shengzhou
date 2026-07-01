import { useState } from 'react'
import { useUserSession } from '../../contexts/UserSessionContext'
import { cn } from '../../lib/cn'
import { CornerCapsule } from '../ui/CornerCapsule'
import { ShenzhouAdminPanel } from './ShenzhouAdminPanel'

type ShenzhouAdminButtonProps = {
  className?: string
  visible?: boolean
}

function ArchiveIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 3 4 7v2h16V7L12 3Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path
        d="M6 11v8a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-8"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M10 14h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

/** 右下角入口：沈昼记忆宫殿 */
export function ShenzhouAdminButton({ className, visible = true }: ShenzhouAdminButtonProps) {
  const [open, setOpen] = useState(false)
  const { sessionId, role } = useUserSession()
  const isDeveloper = role === 'developer'

  if (!visible) return null

  return (
    <>
      <CornerCapsule
        accent
        aria-label={isDeveloper ? 'Memory Palace' : '沈昼记忆宫殿'}
        title={isDeveloper ? 'Memory Palace · 查看沈昼记住了什么' : '查看沈昼记住了什么'}
        onClick={() => setOpen(true)}
        icon={<ArchiveIcon />}
        label="记忆"
        className={cn('fixed bottom-24 right-5 z-50', className)}
      />
      <ShenzhouAdminPanel open={open} onClose={() => setOpen(false)} sessionId={sessionId} />
    </>
  )
}
