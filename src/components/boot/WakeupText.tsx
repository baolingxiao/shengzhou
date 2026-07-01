import { motion } from 'motion/react'
import { cn } from '../../lib/cn'
import { companionGreeting, jarvisTransition } from '../../lib/motion/jarvisMotion'

type WakeupTextProps = {
  visible: boolean
  name?: string
  className?: string
}

/** Companion greeting — 暖白、安静、略带时间感 */
export function WakeupText({
  visible,
  name = 'Jin',
  className,
}: WakeupTextProps) {
  const { lead, name: displayName } = companionGreeting(name)

  return (
    <motion.div
      className={cn('pointer-events-none w-full text-center', className)}
      initial={{ opacity: 0, y: 14, filter: 'blur(6px)' }}
      animate={
        visible
          ? { opacity: 1, y: 0, filter: 'blur(0px)' }
          : { opacity: 0, y: 10, filter: 'blur(4px)' }
      }
      transition={jarvisTransition.greeting}
      aria-hidden={!visible}
    >
      <p className="text-[15px] font-light tracking-[-0.03em] text-jarvis-greeting md:text-base">
        {lead}
        <span className="text-jarvis-text/90">{displayName}</span>
      </p>
    </motion.div>
  )
}
