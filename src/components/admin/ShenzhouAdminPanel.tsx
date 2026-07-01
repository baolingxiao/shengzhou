import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  deleteMemory,
  deleteMemoryMessages,
  fetchMemoryById,
  fetchMemoryDetail,
  fetchMemoryList,
  fetchMemorySummary,
  fetchMemoryTransparency,
  runMemoryMaintenance,
  toggleMemoryMark,
  type ChatHistoryMessage,
  type MemoryItem,
  type MemoryTransparencyRecord,
} from '../../lib/adminApi'
import { parseMemoryChatBody } from '../../lib/parseMemoryChat'
import { filterMemoryItems, type MemoryFilterState } from '../../lib/memoryFilters'
import { MemoryFilters } from '../memory/MemoryFilters'
import { MemoryWorkspace } from '../memory/MemoryWorkspace'
import { MemoryTransparencyList } from './MemoryTransparencyList'
import { MemoryMessageActionSheet } from './MemoryMessageActionSheet'
import {
  formatMaintenanceResponse,
  MemoryMaintenancePanel,
} from '../memory/MemoryMaintenancePanel'
import type { MemoryTabId } from '../memory/MemorySidebar'

type MessageScope = {
  id: string
  relPath?: string
}

type ShenzhouAdminPanelProps = {
  open: boolean
  onClose: () => void
  sessionId: string
}

const DEFAULT_FILTERS: MemoryFilterState = {
  query: '',
  markedOnly: false,
  sort: 'date_desc',
}

export function ShenzhouAdminPanel({ open, onClose, sessionId }: ShenzhouAdminPanelProps) {
  const [tab, setTab] = useState<MemoryTabId>('short')
  const [items, setItems] = useState<MemoryItem[]>([])
  const [transparency, setTransparency] = useState<MemoryTransparencyRecord[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [filters, setFilters] = useState<MemoryFilterState>(DEFAULT_FILTERS)
  const [selected, setSelected] = useState<MemoryItem | null>(null)
  const [detail, setDetail] = useState<{
    memoryId: string
    title: string
    body: string
    messages: ChatHistoryMessage[]
    loading: boolean
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMenu, setActionMenu] = useState<{ scope: MessageScope; index: number } | null>(null)
  const [selectionScope, setSelectionScope] = useState<MessageScope | null>(null)
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set())
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false)

  const filteredItems = useMemo(() => filterMemoryItems(items, filters), [items, filters])

  const scopeForItem = (item: MemoryItem): MessageScope => ({
    id: item.rel_path,
    relPath: item.rel_path,
  })

  const cancelSelection = useCallback(() => {
    setSelectionScope(null)
    setSelectedIndices(new Set())
  }, [])

  const loadSummary = useCallback(async () => {
    const s = await fetchMemorySummary()
    setCounts(s.counts)
  }, [])

  const loadDetail = useCallback(async (item: MemoryItem) => {
    setSelected(item)
    setMobileDetailOpen(true)
    setDetail({
      memoryId: item.memory_id,
      title: item.title,
      body: '',
      messages: [],
      loading: true,
    })
    try {
      const res = await fetchMemoryDetail(item.rel_path)
      const messages = tab === 'short' ? parseMemoryChatBody(res.body) : []
      setDetail({
        memoryId: res.memory_id || item.memory_id,
        title: res.title,
        body: res.body,
        messages,
        loading: false,
      })
    } catch (err) {
      setDetail({
        memoryId: item.memory_id,
        title: item.title,
        body: err instanceof Error ? err.message : '读取失败',
        messages: [],
        loading: false,
      })
    }
  }, [tab])

  const openDetailById = useCallback(async (memoryId: string) => {
    setMobileDetailOpen(true)
    setDetail({
      memoryId,
      title: memoryId,
      body: '',
      messages: [],
      loading: true,
    })
    try {
      const res = await fetchMemoryById(memoryId)
      setDetail({
        memoryId: res.memory_id,
        title: res.title,
        body: res.body,
        messages: parseMemoryChatBody(res.body),
        loading: false,
      })
    } catch (err) {
      setDetail({
        memoryId,
        title: memoryId,
        body: err instanceof Error ? err.message : '读取失败',
        messages: [],
        loading: false,
      })
    }
  }, [])

  const loadTab = useCallback(async (next: MemoryTabId) => {
    setLoading(true)
    setError(null)
    setSelected(null)
    setDetail(null)
    setMobileDetailOpen(false)
    setTransparency([])
    cancelSelection()
    setActionMenu(null)
    setFilters(DEFAULT_FILTERS)
    try {
      if (next === 'transparency') {
        await loadSummary()
        const res = await fetchMemoryTransparency(sessionId)
        setTransparency(res.records)
      } else if (next === 'maintain') {
        await loadSummary()
        setItems([])
      } else {
        await loadSummary()
        const res = await fetchMemoryList(next)
        setItems(res.items)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [loadSummary, sessionId, cancelSelection])

  const refreshAfterMessageDelete = useCallback(async () => {
    await loadSummary()
    if (selected) await loadDetail(selected)
    else await loadTab('short')
  }, [loadSummary, loadDetail, selected, loadTab])

  const handleDeleteMessages = useCallback(
    async (scope: MessageScope, indices: number[]) => {
      if (indices.length === 0) return
      const label = indices.length === 1 ? '这条消息' : `选中的 ${indices.length} 条消息`
      if (!confirm(`确定删除${label}？`)) return
      try {
        await deleteMemoryMessages(indices, { relPath: scope.relPath })
        cancelSelection()
        await refreshAfterMessageDelete()
      } catch (err) {
        setError(err instanceof Error ? err.message : '删除失败')
      }
    },
    [cancelSelection, refreshAfterMessageDelete],
  )

  const handleMessageClick = useCallback(
    (scope: MessageScope, index: number) => {
      if (selectionScope?.id === scope.id) {
        setSelectedIndices((prev) => {
          const next = new Set(prev)
          if (next.has(index)) next.delete(index)
          else next.add(index)
          return next
        })
        return
      }
      setActionMenu({ scope, index })
    },
    [selectionScope],
  )

  useEffect(() => {
    if (!open) return
    void loadTab(tab).catch((err) => {
      setError(err instanceof Error ? err.message : '加载失败')
      setLoading(false)
    })
  }, [open, tab, loadTab])

  const handleTabChange = (next: MemoryTabId) => {
    setTab(next)
  }

  const handleDelete = async (item: MemoryItem) => {
    if (!confirm(`删除「${item.title}」？此操作不可撤销。`)) return
    await deleteMemory(item.rel_path)
    setSelected(null)
    setDetail(null)
    setMobileDetailOpen(false)
    void loadTab(tab)
    void loadSummary()
  }

  const handleMark = async (item: MemoryItem) => {
    await toggleMemoryMark(item.rel_path)
    void loadTab(tab)
  }

  const handleMaintenance = async (action: 'daily' | 'weekly' | 'monthly' | 'catchup') => {
    const res = await runMemoryMaintenance(action, false)
    void loadSummary()
    return formatMaintenanceResponse(res.result)
  }

  const currentScope = selected ? scopeForItem(selected) : null
  const inSelection = Boolean(currentScope && selectionScope?.id === currentScope.id)

  const selectionBar =
    selectionScope && tab === 'short' ? (
      <div className="flex shrink-0 items-center justify-between gap-2 border-t border-jarvis-border bg-jarvis-card px-4 py-3">
        <span className="text-xs text-jarvis-text-muted">已选 {selectedIndices.size} 条</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={cancelSelection}
            className="rounded-jarvis-sm border border-jarvis-border px-3 py-1.5 text-xs text-jarvis-text-muted"
          >
            取消
          </button>
          <button
            type="button"
            disabled={selectedIndices.size === 0}
            onClick={() =>
              void handleDeleteMessages(selectionScope, Array.from(selectedIndices).sort())
            }
            className="rounded-jarvis-sm bg-jarvis-red/20 px-3 py-1.5 text-xs text-jarvis-red disabled:opacity-40"
          >
            删除选中
          </button>
        </div>
      </div>
    ) : null

  return (
    <>
      <MemoryWorkspace
        open={open}
        onClose={onClose}
        tab={tab}
        onTabChange={handleTabChange}
        counts={counts}
        loading={loading}
        error={error}
        filters={<MemoryFilters value={filters} onChange={setFilters} />}
        listItems={filteredItems}
        listEmptyText={
          tab === 'short' ? '暂无短期对话记忆' : tab === 'medium' ? '暂无周期记忆' : '暂无长期记忆'
        }
        shortList={tab === 'short'}
        selectedItem={selected}
        onSelectItem={(item) => void loadDetail(item)}
        onMarkItem={(item) => void handleMark(item)}
        onDeleteItem={(item) => void handleDelete(item)}
        detailMemoryId={detail?.memoryId}
        detailTitle={detail?.title}
        detailBody={detail?.body}
        detailMessages={detail?.messages}
        detailLoading={detail?.loading}
        detailInteractive={tab === 'short'}
        selectionMode={inSelection}
        selectedIndices={inSelection ? selectedIndices : undefined}
        onMessageClick={
          currentScope
            ? (index) => handleMessageClick(currentScope, index)
            : undefined
        }
        onRefresh={() => {
          void loadSummary()
          void loadTab(tab)
        }}
        mobileDetailOpen={mobileDetailOpen}
        onMobileDetailClose={() => {
          setMobileDetailOpen(false)
          setSelected(null)
          setDetail(null)
        }}
        rightContent={
          tab === 'transparency' ? (
            <div>
              <p className="mb-3 text-xs leading-relaxed text-jarvis-text-muted">
                每轮对话中，沈昼为回答你的问题选中了哪些记忆编号（ST/MT/LT）。点击编号可查看详情。
              </p>
              <MemoryTransparencyList
                records={transparency}
                onMemoryIdClick={(id) => void openDetailById(id)}
              />
            </div>
          ) : tab === 'maintain' ? (
            <MemoryMaintenancePanel onRun={handleMaintenance} />
          ) : undefined
        }
        selectionBar={selectionBar}
      />

      <MemoryMessageActionSheet
        open={actionMenu !== null}
        onClose={() => setActionMenu(null)}
        onDeleteOne={() => {
          if (!actionMenu) return
          void handleDeleteMessages(actionMenu.scope, [actionMenu.index])
        }}
        onEnterSelection={() => {
          if (!actionMenu) return
          setSelectionScope(actionMenu.scope)
          setSelectedIndices(new Set([actionMenu.index]))
        }}
      />
    </>
  )
}
