import type { AssetLoader } from './AssetLoader'
import { FISH_SPRITES } from './assets'
import { Fish } from './Fish'
import { rand, randInt } from './math'

export class FishSchool {
  private fish: Fish[] = []
  direction: 1 | -1 = 1
  schoolX = 0
  schoolY = 0
  speedX = 22
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
    this.schoolY = Math.min(this.schoolY, height * 0.82)
  }

  respawn(initial = false): void {
    this.direction = Math.random() < 0.5 ? -1 : 1
    this.speedX = rand(18, 36)
    this.schoolY = rand(this.height * 0.18, this.height * 0.72)

    const count = randInt(4, 8)
    const sprites = [...FISH_SPRITES].sort(() => Math.random() - 0.5).slice(0, count)
    this.fish = sprites.map((sprite, i) => Fish.createRandom(sprite, i, count))

    const margin = 120
    this.schoolX =
      this.direction > 0
        ? initial
          ? rand(-margin, this.width * 0.4)
          : -margin
        : initial
          ? rand(this.width * 0.6, this.width + margin)
          : this.width + margin
  }

  update(dt: number): void {
    this.schoolX += this.direction * this.speedX * dt
    const margin = 140
    if (this.direction > 0 && this.schoolX > this.width + margin) this.respawn()
    if (this.direction < 0 && this.schoolX < -margin) this.respawn()
  }

  draw(ctx: CanvasRenderingContext2D, loader: AssetLoader, time: number): void {
    const sorted = [...this.fish].sort((a, b) => a.offsetY - b.offsetY)
    for (const fish of sorted) {
      fish.draw(ctx, loader, this.schoolX, this.schoolY, this.direction, time)
    }
  }

  static spawnSet(width: number, height: number, count: number): FishSchool[] {
    return Array.from({ length: count }, () => {
      const school = new FishSchool(width, height)
      school.schoolY = rand(height * 0.15, height * 0.78)
      school.speedX = rand(16, 32)
      return school
    })
  }
}
