import { cn } from '../../lib/cn'

type CinematicAtmosphereProps = {
  /** 海洋模式时在画布上叠一层暖雾，避免过冷 */
  oceanBlend?: boolean
  className?: string
}

/** 电影感多层背景：深夜蓝黑 + 雾灰 + 底部暖光 + 暗角 + 颗粒 */
export function CinematicAtmosphere({ oceanBlend, className }: CinematicAtmosphereProps) {
  return (
    <div className={cn('atmosphere-root pointer-events-none absolute inset-0 z-0', className)} aria-hidden>
      <div className="atmosphere-breathe absolute inset-0" />
      <div className="atmosphere-volume-light absolute inset-0" />
      <div className="atmosphere-vignette absolute inset-0" />
      <div className="atmosphere-grain absolute inset-0" />
      {oceanBlend && <div className="atmosphere-ocean-warm absolute inset-0" />}
    </div>
  )
}
