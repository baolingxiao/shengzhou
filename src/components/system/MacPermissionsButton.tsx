import { Shield } from 'lucide-react'
import { useMacPermissionsContext } from '../../contexts/MacPermissionsContext'
import { cn } from '../../lib/cn'
import { CornerCapsule } from '../ui/CornerCapsule'

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
  const statusDot = ready ? 'ok' : partial ? 'warn' : 'alert'

  return (
    <CornerCapsule
      aria-label="系统权限"
      title="系统权限"
      onClick={openStatusPanel}
      icon={<Shield className="h-4 w-4" />}
      label="权限"
      statusDot={statusDot}
      className={cn('fixed bottom-24 left-5 z-50', className)}
    />
  )
}
