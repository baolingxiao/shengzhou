/** SVG viewBox dimensions */
export const VIEWBOX = { width: 400, height: 400, cx: 200, cy: 200 }

/** Organic wave — warm, asymmetric, gently open ring */
export const WAVE_PATH = `
  M 200 118
  C 268 108, 318 158, 312 218
  C 306 278, 248 308, 188 298
  C 128 288, 92 238, 98 178
  C 104 118, 152 128, 200 118
  Z
`.trim()

/** Collapsed wave — tighter inward pull before circle */
export const WAVE_COLLAPSED_PATH = `
  M 200 155
  C 238 150, 262 178, 258 208
  C 254 238, 228 252, 198 248
  C 168 244, 148 222, 150 192
  C 152 162, 172 160, 200 155
  Z
`.trim()

/** Perfect circle — cubic-bezier approximation for smooth flubber morph */
export const CIRCLE_PATH = `
  M 200 140
  C 233.137 140, 260 166.863, 260 200
  C 260 233.137, 233.137 260, 200 260
  C 166.863 260, 140 233.137, 140 200
  C 140 166.863, 166.863 140, 200 140
  Z
`.trim()

export const CIRCLE_RADIUS = 60
