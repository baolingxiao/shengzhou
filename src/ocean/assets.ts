export const MARINE_BASE = '/assets/marine/海鲜市场'

export const FISH_SPRITES = [
  ...Array.from({ length: 16 }, (_, i) => `鱼-${String(i + 1).padStart(2, '0')}.png`),
  '鱼-大.png',
  '鱼-双.png',
]

export const BUBBLE_SPRITES = Array.from(
  { length: 8 },
  (_, i) => `气泡-${String(i + 1).padStart(2, '0')}.png`,
)

export const WANDER_SPRITES = [
  '虾-左.png',
  '虾-中.png',
  '虾-右.png',
  '海胆.png',
  '海星.png',
  '鹦鹉螺.png',
  '海绵.png',
  '海葵.png',
  '河豚.png',
]

/** 固定在页面底部的珊瑚 / 海草（不参与 wander） */
export const GROUND_SPRITES = [
  '海草-左.png',
  '珊瑚-枝-左.png',
  '珊瑚-小.png',
  '海草-浪.png',
  '珊瑚-枝-右.png',
  '海草-右.png',
]

export const GROUND_DECOR_LAYOUT = [
  { sprite: '海草-左.png', xRatio: 0.05, scale: 0.95, bottomInset: 8 },
  { sprite: '珊瑚-枝-左.png', xRatio: 0.16, scale: 0.88, bottomInset: 4 },
  { sprite: '珊瑚-小.png', xRatio: 0.34, scale: 0.82, bottomInset: 10 },
  { sprite: '海草-浪.png', xRatio: 0.52, scale: 1.0, bottomInset: 6 },
  { sprite: '珊瑚-枝-右.png', xRatio: 0.72, scale: 0.9, bottomInset: 4 },
  { sprite: '海草-右.png', xRatio: 0.93, scale: 0.95, bottomInset: 8 },
] as const

export const FLOATING_SPRITES = ['水母.png', '鱿鱼.png', '鱿鱼-大.png', '鱿鱼-小.png']

export const ALL_SPRITES = [
  ...new Set([
    ...FISH_SPRITES,
    ...BUBBLE_SPRITES,
    ...WANDER_SPRITES,
    ...GROUND_SPRITES,
    ...FLOATING_SPRITES,
  ]),
]

export function assetUrl(file: string): string {
  return `${MARINE_BASE}/${encodeURIComponent(file)}`
}
