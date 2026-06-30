import { motion } from 'motion/react'
import { cn } from '../../lib/cn'
import { fadeTransition } from '../../motion/springs'

type WakeupTextProps = {
  visible: boolean
  name?: string
  className?: string
}

/** Greeting — sits above the Rose animation in the layout stack */
export function WakeupText({
  visible,
  name = 'Jin',
  className,
}: WakeupTextProps) {
  return (
    <motion.div
      className={cn('pointer-events-none w-full text-center', className)}
      initial={{ opacity: 0, y: 10 }}
      animate={visible ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
      transition={fadeTransition}
      aria-hidden={!visible}
    >
      <p className="text-3xl font-light tracking-tight text-foreground md:text-4xl">
        Hello, {name}.
      </p>
    </motion.div>
  )
}
