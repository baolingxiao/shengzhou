import type { MemoryItem } from './adminApi'

export type MemoryFilterState = {
  query: string
  markedOnly: boolean
  sort: 'date_desc' | 'date_asc'
}

export function filterMemoryItems(items: MemoryItem[], filters: MemoryFilterState): MemoryItem[] {
  let out = [...items]
  const q = filters.query.trim().toLowerCase()
  if (q) {
    out = out.filter(
      (item) =>
        item.memory_id.toLowerCase().includes(q) ||
        item.title.toLowerCase().includes(q) ||
        item.preview.toLowerCase().includes(q) ||
        item.rel_path.toLowerCase().includes(q),
    )
  }
  if (filters.markedOnly) {
    out = out.filter((item) => item.marked)
  }
  out.sort((a, b) =>
    filters.sort === 'date_asc'
      ? a.modified_at - b.modified_at
      : b.modified_at - a.modified_at,
  )
  return out
}
