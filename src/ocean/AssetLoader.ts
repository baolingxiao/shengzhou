import { ALL_SPRITES, assetUrl } from './assets'

export class AssetLoader {
  private images = new Map<string, HTMLImageElement>()
  private loadPromise: Promise<void> | null = null

  async load(): Promise<void> {
    if (this.loadPromise) return this.loadPromise
    this.loadPromise = Promise.all(ALL_SPRITES.map((file) => this.loadOne(file))).then(() => undefined)
    return this.loadPromise
  }

  get(file: string): HTMLImageElement | undefined {
    return this.images.get(file)
  }

  isReady(): boolean {
    return this.images.size === ALL_SPRITES.length
  }

  private loadOne(file: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.decoding = 'async'
      img.onload = () => {
        this.images.set(file, img)
        resolve()
      }
      img.onerror = () => reject(new Error(`Failed to load marine asset: ${file}`))
      img.src = assetUrl(file)
    })
  }
}
