import { cn } from '../../lib/cn'

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
    <button
      type="button"
      onClick={onClick}
      aria-label="用户信息"
      title="用户信息"
      className={cn(
        'flex h-9 items-center gap-1.5 rounded-full px-3',
        'border border-white/20 bg-[rgba(55,82,92,0.32)] text-white/80',
        'shadow-[0_4px_24px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.14)]',
        'backdrop-blur-xl backdrop-saturate-150',
        'transition-[background-color,box-shadow,transform,color] duration-300 ease-out',
        'hover:border-white/28 hover:bg-[rgba(70,106,119,0.42)] hover:text-white',
        'active:scale-95',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/25',
        className,
      )}
    >
      <UserIcon className="h-[16px] w-[16px]" />
      <span className="text-xs font-medium">{label}</span>
    </button>
  )
}
