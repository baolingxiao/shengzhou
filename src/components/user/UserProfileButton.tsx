import { CornerCapsule } from '../ui/CornerCapsule'

type UserProfileButtonProps = {
  onClick: () => void
  className?: string
  label?: string
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M5 20c0-3.3 3.1-6 7-6s7 2.7 7 6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

/** 左上角用户信息入口 */
export function UserProfileButton({ onClick, className, label = '用户' }: UserProfileButtonProps) {
  return (
    <CornerCapsule
      onClick={onClick}
      aria-label="用户信息"
      title="用户信息"
      icon={<UserIcon className="h-4 w-4" />}
      label={label}
      className={className}
    />
  )
}
