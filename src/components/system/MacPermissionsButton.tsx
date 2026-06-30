import { Shield } from 'lucide-react'
import { useMacPermissionsContext } from '../../contexts/MacPermissionsContext'
import { cn } from '../../lib/cn'

type MacPermissionsButtonProps = {
  className?: string
  visible?: boolean
}

/** 左下角入口：查看贾维斯当前系统权限 */
export function MacPermissionsButton({ className, visible = true }: MacPermissionsButtonProps) {
  const { snapshot, openStatusPanel } = useMacPermissionsContext()

  if (!visible || snapshot?.platform !== 'Darwin') return null

  const ready = snapshot.all_granted
  const partial = snapshot.system_permissions_granted && !snapshot.all_granted

  return (
    <button
      type="button"
      aria-label="系统权限"
      title="系统权限"
      onClick={openStatusPanel}
      className={cn(
        'fixed bottom-24 left-5 z-50 flex h-11 items-center gap-2 rounded-full',
        'border border-white/20 bg-[#12141a]/90 px-4 text-sm text-foreground/90',
        'shadow-lg backdrop-blur-md transition hover:border-white/35 hover:bg-[#1a1d26]',
        className,
      )}
    >
      <span className="relative text-base opacity-80" aria-hidden>
        <Shield className="h-4 w-4" />
        <span
          className={cn(
            'absolute -right-1 -top-1 h-2 w-2 rounded-full',
            ready ? 'bg-emerald-400' : partial ? 'bg-amber-400' : 'bg-red-400',
          )}
        />
      </span>
      权限
    </button>
  )
}
