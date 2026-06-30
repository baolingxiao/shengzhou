export const ROSE_TWO_CONFIG = {
  name: 'Rose Two',
  tag: 'r = a cos(2θ)',
  rotate: true,
  particleCount: 116,
  trailSpan: 0.3,
  durationMs: 6100,
  rotationDurationMs: 28000,
  pulseDurationMs: 4300,
  strokeWidth: 4.6,
  roseA: 9.2,
  roseABoost: 0.6,
  roseBreathBase: 0.72,
  roseBreathBoost: 0.28,
  roseScale: 3.25,
  pathSteps: 480,
  center: 50,
} as const

export type RoseTwoConfig = typeof ROSE_TWO_CONFIG

export type RoseTwoPoint = { x: number; y: number }

export type RoseTwoParticle = RoseTwoPoint & {
  radius: number
  opacity: number
}

export function roseTwoPoint(
  progress: number,
  detailScale: number,
  config: RoseTwoConfig = ROSE_TWO_CONFIG,
): RoseTwoPoint {
  const t = progress * Math.PI * 2
  const a = config.roseA + detailScale * config.roseABoost
  const r =
    a *
    (config.roseBreathBase + detailScale * config.roseBreathBoost) *
    Math.cos(2 * t)

  return {
    x: config.center + Math.cos(t) * r * config.roseScale,
    y: config.center + Math.sin(t) * r * config.roseScale,
  }
}

export function normalizeProgress(progress: number) {
  return ((progress % 1) + 1) % 1
}

export function getRoseDetailScale(timeMs: number, config: RoseTwoConfig = ROSE_TWO_CONFIG) {
  const pulseProgress = (timeMs % config.pulseDurationMs) / config.pulseDurationMs
  const pulseAngle = pulseProgress * Math.PI * 2
  return 0.52 + ((Math.sin(pulseAngle + 0.55) + 1) / 2) * 0.48
}

export function getRoseRotation(timeMs: number, config: RoseTwoConfig = ROSE_TWO_CONFIG) {
  if (!config.rotate) return 0
  return -((timeMs % config.rotationDurationMs) / config.rotationDurationMs) * 360
}

export function buildRosePath(
  detailScale: number,
  config: RoseTwoConfig = ROSE_TWO_CONFIG,
) {
  const steps = config.pathSteps
  return Array.from({ length: steps + 1 }, (_, index) => {
    const point = roseTwoPoint(index / steps, detailScale, config)
    return `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`
  }).join(' ')
}

export function getRoseParticle(
  index: number,
  progress: number,
  detailScale: number,
  config: RoseTwoConfig = ROSE_TWO_CONFIG,
): RoseTwoParticle {
  const tailOffset = index / (config.particleCount - 1)
  const point = roseTwoPoint(
    normalizeProgress(progress - tailOffset * config.trailSpan),
    detailScale,
    config,
  )
  const fade = Math.pow(1 - tailOffset, 0.56)

  return {
    x: point.x,
    y: point.y,
    radius: 0.9 + fade * 2.7,
    opacity: 0.04 + fade * 0.96,
  }
}

export function getRoseFrame(timeMs: number, config: RoseTwoConfig = ROSE_TWO_CONFIG) {
  const progress = (timeMs % config.durationMs) / config.durationMs
  const detailScale = getRoseDetailScale(timeMs, config)
  const rotation = getRoseRotation(timeMs, config)
  const path = buildRosePath(detailScale, config)
  const particles = Array.from({ length: config.particleCount }, (_, index) =>
    getRoseParticle(index, progress, detailScale, config),
  )

  return { progress, detailScale, rotation, path, particles }
}

export function roseTwoFormula(config: RoseTwoConfig = ROSE_TWO_CONFIG) {
  return [
    `r(t) = (${config.roseA.toFixed(1)} + ${config.roseABoost.toFixed(2)}s)(${config.roseBreathBase.toFixed(2)} + ${config.roseBreathBoost.toFixed(2)}s) cos(2t)`,
    `x(t) = ${config.center} + cos t · r(t) · ${config.roseScale.toFixed(2)}`,
    `y(t) = ${config.center} + sin t · r(t) · ${config.roseScale.toFixed(2)}`,
  ].join('\n')
}
