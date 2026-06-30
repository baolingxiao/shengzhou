/** Soft breathing transitions — no bounce, no cartoon elasticity */
export const breatheTransition = {
  duration: 2.4,
  repeat: Infinity,
  ease: [0.22, 1, 0.36, 1] as const,
}

export const fadeTransition = {
  duration: 1.0,
  ease: [0.22, 1, 0.36, 1] as const,
}

export const revealTransition = {
  duration: 1.2,
  ease: [0.22, 1, 0.36, 1] as const,
}
