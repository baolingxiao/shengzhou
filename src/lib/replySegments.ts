const SEGMENT_DELAY_BASE_MS = 380
const SEGMENT_DELAY_PER_CHAR_MS = 28

export function delayForSegment(text: string, index: number): number {
  if (index <= 0) return 0
  return SEGMENT_DELAY_BASE_MS + Math.min(text.length, 40) * SEGMENT_DELAY_PER_CHAR_MS
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}
