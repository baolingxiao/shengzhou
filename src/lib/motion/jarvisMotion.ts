/** Jarvis · 统一动效 token（Apple / VisionOS 风格） */
export const jarvisMotion = {
  spring: {
    type: 'spring' as const,
    damping: 28,
    stiffness: 320,
  },
  softSpring: {
    type: 'spring' as const,
    damping: 34,
    stiffness: 220,
  },
  fadeUp: {
    initial: { opacity: 0, y: 22 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 14 },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.96 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.98 },
  },
  breathe: {
    animate: { scale: [1, 1.035, 1], opacity: [0.88, 1, 0.88] },
    transition: { duration: 4.8, repeat: Infinity, ease: 'easeInOut' as const },
  },
  slowAtmosphere: {
    animate: { opacity: [0.94, 1, 0.94] },
    transition: { duration: 24, repeat: Infinity, ease: 'easeInOut' as const },
  },
}

export const jarvisTransition = {
  panel: jarvisMotion.softSpring,
  sheet: jarvisMotion.spring,
  fade: { duration: 0.38, ease: [0.22, 1, 0.36, 1] as const },
  greeting: { duration: 0.65, delay: 0.2, ease: [0.22, 1, 0.36, 1] as const },
  composerFocus: { duration: 0.22, ease: [0.22, 1, 0.36, 1] as const },
}

export function companionGreeting(name: string): { lead: string; name: string } {
  const h = new Date().getHours()
  if (h >= 5 && h < 11) return { lead: '早上好，', name }
  if (h >= 11 && h < 17) return { lead: '下午好，', name }
  if (h >= 17 && h < 23) return { lead: '晚上好，', name }
  return { lead: '还没睡吗，', name }
}

export function companionEmptyHint(): string {
  const h = new Date().getHours()
  if (h >= 23 || h < 5) return '夜深了。我在听。'
  return '我在。想从哪里开始？'
}
