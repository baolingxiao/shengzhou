import type { AssetLoader } from './AssetLoader'
import { BUBBLE_SPRITES } from './assets'
import { pick, rand, randInt } from './math'

type ClusterBubble = {
  sprite: string
  offsetX: number
  offsetY: number
  radius: number
  alpha: number
  wobbleSpeed: number
  wobbleAmount: number
  phase: number
}

export class BubbleCluster {
  clusterX = 0
  clusterY = 0
  speedY = 14
  private bubbles: ClusterBubble[] = []
  private width: number
  private height: number

  constructor(width: number, height: number) {
    this.width = width
    this.height = height
    this.respawn(true)
  }

  resize(width: number, height: number): void {
    this.width = width
    this.height = height
  }

  respawn(initial = false): void {
    this.clusterX = rand(this.width * 0.08, this.width * 0.92)
    this.clusterY = initial ? rand(this.height * 0.35, this.height * 0.95) : this.height + rand(40, 120)
    this.speedY = rand(14, 26)

    const count = randInt(5, 15)
    this.bubbles = Array.from({ length: count }, () => ({
      sprite: pick(BUBBLE_SPRITES),
      offsetX: rand(-55, 55),
      offsetY: rand(-30, 30),
      radius: rand(6, 22),
      alpha: rand(0.18, 0.55),
      wobbleSpeed: rand(0.6, 1.4),
      wobbleAmount: rand(3, 10),
      phase: rand(0, Math.PI * 2),
    }))
  }

  update(dt: number): void {
    this.clusterY -= this.speedY * dt
    const top = Math.min(...this.bubbles.map((b) => b.offsetY)) + this.clusterY
    if (top < -80) this.respawn()
  }

  draw(ctx: CanvasRenderingContext2D, loader: AssetLoader, time: number): void {
    for (const bubble of this.bubbles) {
      const img = loader.get(bubble.sprite)
      if (!img) continue

      const wobble = Math.sin(time * bubble.wobbleSpeed + bubble.phase) * bubble.wobbleAmount
      const x = this.clusterX + bubble.offsetX + wobble
      const y = this.clusterY + bubble.offsetY
      const size = bubble.radius * 2

      ctx.save()
      ctx.globalAlpha = bubble.alpha
      ctx.drawImage(img, x - size / 2, y - size / 2, size, size)
      ctx.restore()
    }
  }

  static spawnSet(width: number, height: number, count: number): BubbleCluster[] {
    return Array.from({ length: count }, (_, i) => {
      const cluster = new BubbleCluster(width, height)
      cluster.clusterY = height + i * rand(80, 160)
      return cluster
    })
  }
}
