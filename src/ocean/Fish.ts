import type { AssetLoader } from './AssetLoader'
import { rand } from './math'

export type FishConfig = {
  sprite: string
  offsetX: number
  offsetY: number
  scale: number
  alpha: number
  bobPhase: number
  bobSpeed: number
  bobAmount: number
}

export class Fish {
  readonly sprite: string
  readonly offsetX: number
  readonly offsetY: number
  readonly scale: number
  readonly alpha: number
  readonly bobPhase: number
  readonly bobSpeed: number
  readonly bobAmount: number

  constructor(config: FishConfig) {
    this.sprite = config.sprite
    this.offsetX = config.offsetX
    this.offsetY = config.offsetY
    this.scale = config.scale
    this.alpha = config.alpha
    this.bobPhase = config.bobPhase
    this.bobSpeed = config.bobSpeed
    this.bobAmount = config.bobAmount
  }

  static createRandom(sprite: string, index: number, spread: number): Fish {
    return new Fish({
      sprite,
      offsetX: (index - spread / 2) * rand(28, 42) + rand(-8, 8),
      offsetY: rand(-22, 22),
      scale: rand(0.35, 0.75),
      alpha: rand(0.45, 0.88),
      bobPhase: rand(0, Math.PI * 2),
      bobSpeed: rand(0.8, 1.6),
      bobAmount: rand(4, 11),
    })
  }

  draw(
    ctx: CanvasRenderingContext2D,
    loader: AssetLoader,
    schoolX: number,
    schoolY: number,
    direction: 1 | -1,
    time: number,
  ): void {
    const img = loader.get(this.sprite)
    if (!img) return

    const bob = Math.sin(time * this.bobSpeed + this.bobPhase) * this.bobAmount
    const x = schoolX + this.offsetX
    const y = schoolY + this.offsetY + bob
    const w = img.naturalWidth * this.scale
    const h = img.naturalHeight * this.scale

    ctx.save()
    ctx.globalAlpha = this.alpha
    ctx.translate(x, y)
    if (direction < 0) ctx.scale(-1, 1)
    ctx.drawImage(img, -w / 2, -h / 2, w, h)
    ctx.restore()
  }
}
