import { AssetLoader } from './AssetLoader'
import { BubbleCluster } from './BubbleCluster'
import { FishSchool } from './FishSchool'
import { FloatingCreature } from './FloatingCreature'
import { GroundDecor } from './GroundDecor'
import { WanderCreature } from './WanderCreature'

export class OceanScene {
  readonly loader = new AssetLoader()
  private fishSchools: FishSchool[] = []
  private bubbleClusters: BubbleCluster[] = []
  private wanderCreatures: WanderCreature[] = []
  private floatingCreatures: FloatingCreature[] = []
  private groundDecors: GroundDecor[] = []
  private width = 0
  private height = 0
  private time = 0
  private ready = false
  private motionScale = 1

  async init(width: number, height: number): Promise<void> {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    this.motionScale = reduced ? 0.35 : 1
    await this.loader.load()
    this.resize(width, height)
    this.ready = true
  }

  resize(width: number, height: number): void {
    if (width <= 0 || height <= 0) return
    this.width = width
    this.height = height
    if (this.fishSchools.length === 0) {
      this.groundDecors = GroundDecor.spawnSet(width, height)
      this.fishSchools = FishSchool.spawnSet(width, height, 3)
      this.bubbleClusters = BubbleCluster.spawnSet(width, height, 3)
      this.wanderCreatures = WanderCreature.spawnSet(width, height, 7)
      this.floatingCreatures = FloatingCreature.spawnSet(width, height, 3)
      return
    }
    for (const d of this.groundDecors) d.resize(width, height)
    for (const s of this.fishSchools) s.resize(width, height)
    for (const c of this.bubbleClusters) c.resize(width, height)
    for (const w of this.wanderCreatures) w.resize(width, height)
    for (const f of this.floatingCreatures) f.resize(width, height)
  }

  update(dt: number): void {
    if (!this.ready) return

    const scaled = dt * this.motionScale
    this.time += scaled

    for (const school of this.fishSchools) school.update(scaled)
    for (const cluster of this.bubbleClusters) cluster.update(scaled)
    for (const creature of this.wanderCreatures) creature.update(scaled, this.time)
    for (const creature of this.floatingCreatures) creature.update(scaled)
  }

  draw(ctx: CanvasRenderingContext2D): void {
    if (!this.ready) return

    ctx.clearRect(0, 0, this.width, this.height)
    this.drawBackdrop(ctx)

    for (const decor of this.groundDecors) decor.draw(ctx, this.loader)
    for (const creature of this.wanderCreatures) creature.draw(ctx, this.loader, this.time)
    for (const creature of this.floatingCreatures) creature.draw(ctx, this.loader, this.time)
    for (const school of this.fishSchools) school.draw(ctx, this.loader, this.time)
    for (const cluster of this.bubbleClusters) cluster.draw(ctx, this.loader, this.time)
  }

  private drawBackdrop(ctx: CanvasRenderingContext2D): void {
    const g = ctx.createRadialGradient(
      this.width * 0.5,
      this.height * 0.42,
      0,
      this.width * 0.5,
      this.height * 0.5,
      Math.max(this.width, this.height) * 0.75,
    )
    g.addColorStop(0, 'rgba(70, 106, 119, 0.35)')
    g.addColorStop(0.45, 'rgba(47, 73, 82, 0.28)')
    g.addColorStop(0.75, 'rgba(27, 42, 48, 0.22)')
    g.addColorStop(1, 'rgba(15, 15, 20, 0.15)')
    ctx.fillStyle = g
    ctx.fillRect(0, 0, this.width, this.height)
  }
}
