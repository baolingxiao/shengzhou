export const THINKING_STATUS_LABEL = '对方正在输入......'

const THINKING_TOKENS = new Set([
  'thinking',
  'thinking...',
  'thinking…',
  'typing',
  'typing...',
  'typing…',
])

/**
 * Normalize raw status text from different UI paths.
 * Only remaps labels that semantically mean "thinking/typing".
 */
export function normalizeThinkingStatusLabel(label: string): string {
  const normalized = label.trim().toLowerCase()
  if (THINKING_TOKENS.has(normalized)) {
    return THINKING_STATUS_LABEL
  }
  if (/(?:^|[\s·:：-])(thinking|typing)(?:\.{3}|…)?$/i.test(normalized)) {
    return label.replace(/\b(?:thinking|typing)(?:\.{3}|…)?\b/gi, THINKING_STATUS_LABEL)
  }
  return label
}
