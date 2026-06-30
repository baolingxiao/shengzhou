import { useEffect, useRef } from 'react'
import { cn } from '../../lib/cn'
import { OceanScene } from '../../ocean/OceanScene'

type OceanBackgroundProps = {
  className?: string
  active?: boolean
}

export function OceanBackground({ className, active = true }: OceanBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const frameRef = useRef<number>(0)
  const activeRef = useRef(active)

  useEffect(() => {
    activeRef.current = active
  }, [active])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    let alive = true
    const scene = new OceanScene()
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let ready = false
    let last = performance.now()

    const resize = () => {
      const parent = canvas.parentElement
      if (!parent) return
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = parent.clientWidth
      const h = parent.clientHeight
      if (w <= 0 || h <= 0) return

      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      scene.resize(w, h)
    }

    const tick = (now: number) => {
      if (!alive) return
      const dt = Math.min((now - last) / 1000, 0.05)
      last = now
      if (ready && activeRef.current) {
        scene.update(dt)
        scene.draw(ctx)
      }
      frameRef.current = requestAnimationFrame(tick)
    }

    frameRef.current = requestAnimationFrame(tick)

    void scene
      .init(canvas.parentElement?.clientWidth ?? window.innerWidth, canvas.parentElement?.clientHeight ?? window.innerHeight)
      .then(() => {
        if (!alive) return
        ready = true
        resize()
      })
      .catch((err) => {
        console.error('[OceanBackground] failed to init', err)
      })

    const ro = new ResizeObserver(resize)
    if (canvas.parentElement) ro.observe(canvas.parentElement)
    window.addEventListener('resize', resize)

    return () => {
      alive = false
      cancelAnimationFrame(frameRef.current)
      ro.disconnect()
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className={cn(
        'pointer-events-none absolute inset-0 z-[1] transition-opacity duration-700 ease-out',
        active ? 'opacity-100' : 'opacity-0',
        className,
      )}
      aria-hidden
    />
  )
}
