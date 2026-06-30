import type { AssetLoader } from './AssetLoader'
import { FLOATING_SPRITES } from './assets'
import { pick, rand } from './math'

export class FloatingCreature {
  baseX = 0
  baseY = 0
  private width = 0
  private readonly sprite: string
  private readonly scale: number
  private readonly alpha: number
  private readonly breatheSpeed: number
  private readonly breatheAmount: number
  private readonly swaySpeed: number
  private readonly swayAmount: number
  private readonly driftSpeed: number
  private readonly phase: number
  private driftX = 0

  constructor(
    width: number,
    height: number,
    sprite?: string,
  ) {
    this.sprite = sprite ?? pick(FLOATING_SPRITES)
    this.scale = rand(0.5, 0.95)
    this.alpha = rand(0.5, 0.85)
    this.breatheSpeed = rand(0.25, 0.45)
    this.breatheAmount = rand(10, 22)
    this.swaySpeed = rand(0.15, 0.32)
    this.swayAmount = rand(12, 28)
    this.driftSpeed = rand(4, 10)
    this.phase = rand(0, Math.PI * 2)
    this.width = width
    this.baseX = rand(width * 0.12, width * 0.88)
    this.baseY = rand(height * 0.15, height * 0.7)
    this.driftX = rand(-1, 1)
  }

  resize(width: number, height: number): void {
    this.width = width
    this.baseX = Math.min(this.baseX, width * 0.9)
    this.baseY = Math.min(this.baseY, height * 0.75)
  }

  update(dt: number): void {
    this.baseX += this.driftX * this.driftSpeed * dt * 0.25
    if (this.baseX < 40 || this.baseX > this.width - 40) this.driftX *= -1
  }

  draw(ctx: CanvasRenderingContext2D, loader: AssetLoader, time: number): void {
    const img = loader.get(this.sprite)
    if (!img) return

    const breathe = Math.sin(time * this.breatheSpeed + this.phase) * this.breatheAmount
    const sway = Math.sin(time * this.swaySpeed + this.phase * 1.3) * this.swayAmount
    const x = this.baseX + sway
    const y = this.baseY + breathe
    const w = img.naturalWidth * this.scale
    const h = img.naturalHeight * this.scale

    ctx.save()
    ctx.globalAlpha = this.alpha
    ctx.translate(x, y)
    ctx.rotate(Math.sin(time * 0.2 + this.phase) * 0.04)
    ctx.drawImage(img, -w / 2, -h / 2, w, h)
    ctx.restore()
  }

  static spawnSet(width: number, height: number, count: number): FloatingCreature[] {
    return Array.from({ length: count }, () => new FloatingCreature(width, height))
  }
}
