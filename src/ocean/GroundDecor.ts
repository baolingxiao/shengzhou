import type { AssetLoader } from './AssetLoader'
import { GROUND_DECOR_LAYOUT } from './assets'

type DecorSpec = {
  sprite: string
  xRatio: number
  scale: number
  bottomInset: number
}

export class GroundDecor {
  private readonly spec: DecorSpec
  private width = 0
  private height = 0

  constructor(spec: DecorSpec) {
    this.spec = spec
  }

  resize(width: number, height: number): void {
    this.width = width
    this.height = height
  }

  draw(ctx: CanvasRenderingContext2D, loader: AssetLoader): void {
    const img = loader.get(this.spec.sprite)
    if (!img || this.width <= 0 || this.height <= 0) return

    const w = img.naturalWidth * this.spec.scale
    const h = img.naturalHeight * this.spec.scale
    const x = this.width * this.spec.xRatio
    const y = this.height - this.spec.bottomInset

    ctx.save()
    ctx.globalAlpha = 0.88
    ctx.translate(x, y)
    ctx.drawImage(img, -w / 2, -h, w, h)
    ctx.restore()
  }

  static spawnSet(width: number, height: number): GroundDecor[] {
    return GROUND_DECOR_LAYOUT.map((spec) => {
      const decor = new GroundDecor(spec)
      decor.resize(width, height)
      return decor
    })
  }
}
