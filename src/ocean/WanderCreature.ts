import type { AssetLoader } from './AssetLoader'
import { WANDER_SPRITES } from './assets'
import { pick, rand } from './math'

export class WanderCreature {
  x = 0
  y = 0
  private targetX = 0
  private targetY = 0
  private state: 'moving' | 'idle' = 'moving'
  private idleUntil = 0
  private readonly sprite: string
  private readonly scale: number
  private readonly alpha: number
  private readonly speed: number
  private readonly swayPhase: number
  private width: number
  private height: number

  constructor(width: number, height: number, sprite?: string) {
    this.width = width
    this.height = height
    this.sprite = sprite ?? pick(WANDER_SPRITES)
    this.scale = rand(0.45, 0.85)
    this.alpha = rand(0.55, 0.92)
    this.speed = rand(8, 18)
    this.swayPhase = rand(0, Math.PI * 2)
    this.x = rand(width * 0.1, width * 0.9)
    this.y = rand(height * 0.2, height * 0.85)
    this.pickTarget()
  }

  resize(width: number, height: number): void {
    this.width = width
    this.height = height
    this.x = Math.min(this.x, width * 0.92)
    this.y = Math.min(this.y, height * 0.9)
  }

  private pickTarget(): void {
    const padX = this.width * 0.1
    const padTop = this.height * 0.12
    const padBottom = this.height * 0.22
    this.targetX = rand(padX, this.width - padX)
    this.targetY = rand(padTop, this.height - padBottom)
    this.state = 'moving'
  }

  update(dt: number, time: number): void {
    if (this.state === 'idle') {
      if (time >= this.idleUntil) this.pickTarget()
      return
    }

    const dx = this.targetX - this.x
    const dy = this.targetY - this.y
    const dist = Math.hypot(dx, dy)
    if (dist < 5) {
      this.state = 'idle'
      this.idleUntil = time + rand(1, 4)
      return
    }

    const move = this.speed * dt
    const step = Math.min(move, dist)
    this.x += (dx / dist) * step
    this.y += (dy / dist) * step
  }

  draw(ctx: CanvasRenderingContext2D, loader: AssetLoader, time: number): void {
    const img = loader.get(this.sprite)
    if (!img) return

    const sway = Math.sin(time * 0.5 + this.swayPhase) * 2.5
    const w = img.naturalWidth * this.scale
    const h = img.naturalHeight * this.scale

    ctx.save()
    ctx.globalAlpha = this.alpha
    ctx.translate(this.x + sway, this.y)
    ctx.drawImage(img, -w / 2, -h / 2, w, h)
    ctx.restore()
  }

  static spawnSet(width: number, height: number, count: number): WanderCreature[] {
    const sprites = [...WANDER_SPRITES].sort(() => Math.random() - 0.5)
    return Array.from({ length: count }, (_, i) => new WanderCreature(width, height, sprites[i % sprites.length]))
  }
}
