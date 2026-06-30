import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { cn } from '../../lib/cn'
import { DEFAULT_CHARACTER_NAME } from '../../lib/characterConfig'
import {
  clearChatSession,
  deleteMemory,
  deleteMemoryMessages,
  fetchChatHistory,
  fetchMemoryDetail,
  fetchMemoryList,
  fetchMemorySummary,
  runMemoryMaintenance,
  toggleMemoryMark,
  type ChatHistoryMessage,
  type MemoryItem,
  type MemoryTier,
} from '../../lib/adminApi'
import { parseMemoryChatBody, shortMemorySessionLabel } from '../../lib/parseMemoryChat'
import { MemoryChatBubbles } from './MemoryChatBubbles'
import { MemoryMessageActionSheet } from './MemoryMessageActionSheet'

type TabId = 'short' | 'medium' | 'long' | 'chat' | 'maintain'

type ShortSessionView = {
  item: MemoryItem
  messages: ChatHistoryMessage[]
}

type MessageScope = {
  id: string
  relPath?: string
  useLiveSession?: boolean
}

const LIVE_CHAT_SCOPE_ID = '__live_chat__'

const TABS: { id: TabId; label: string; tier?: MemoryTier }[] = [
  { id: 'short', label: '短期', tier: 'short' },
  { id: 'medium', label: '中期', tier: 'medium' },
  { id: 'long', label: '长期', tier: 'long' },
  { id: 'chat', label: '聊天记录' },
  { id: 'maintain', label: '清洗维护' },
]

type ShenzhouAdminPanelProps = {
  open: boolean
  onClose: () => void
  sessionId: string
}

export function ShenzhouAdminPanel({ open, onClose, sessionId }: ShenzhouAdminPanelProps) {
  const [tab, setTab] = useState<TabId>('short')
  const [items, setItems] = useState<MemoryItem[]>([])
  const [shortSessions, setShortSessions] = useState<ShortSessionView[]>([])
  const [chat, setChat] = useState<ChatHistoryMessage[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [selected, setSelected] = useState<MemoryItem | null>(null)
  const [detail, setDetail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [maintainLog, setMaintainLog] = useState<string>('')
  const [actionMenu, setActionMenu] = useState<{ scope: MessageScope; index: number } | null>(null)
  const [selectionScope, setSelectionScope] = useState<MessageScope | null>(null)
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set())

  const scopeForItem = (item: MemoryItem): MessageScope => ({
    id: item.rel_path,
    relPath: item.rel_path,
  })

  const liveChatScope: MessageScope = {
    id: LIVE_CHAT_SCOPE_ID,
    useLiveSession: true,
  }

  const cancelSelection = useCallback(() => {
    setSelectionScope(null)
    setSelectedIndices(new Set())
  }, [])

  const loadSummary = useCallback(async () => {
    const s = await fetchMemorySummary()
    setCounts(s.counts)
  }, [])

  const loadTab = useCallback(async (next: TabId) => {
    setLoading(true)
    setError(null)
    setSelected(null)
    setDetail('')
    setShortSessions([])
    cancelSelection()
    setActionMenu(null)
    try {
      if (next === 'chat') {
        await loadSummary()
        const res = await fetchChatHistory(sessionId)
        setChat(res.messages)
      } else if (next === 'maintain') {
        await loadSummary()
      } else {
        const tier = TABS.find((t) => t.id === next)?.tier
        if (!tier) return
        await loadSummary()
        const res = await fetchMemoryList(tier)
        setItems(res.items)
        if (tier === 'short' && res.items.length > 0) {
          const sessions = await Promise.all(
            res.items.map(async (item) => {
              try {
                const detail = await fetchMemoryDetail(item.rel_path)
                return {
                  item,
                  messages: parseMemoryChatBody(detail.body),
                }
              } catch {
                return { item, messages: [] as ChatHistoryMessage[] }
              }
            }),
          )
          setShortSessions(sessions)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [loadSummary, sessionId, cancelSelection])

  const refreshAfterMessageDelete = useCallback(
    async (scope: MessageScope) => {
      await loadSummary()
      if (scope.useLiveSession) {
        const res = await fetchChatHistory(sessionId)
        setChat(res.messages)
      } else {
        await loadTab('short')
      }
    },
    [loadSummary, loadTab, sessionId],
  )

  const handleDeleteMessages = useCallback(
    async (scope: MessageScope, indices: number[]) => {
      if (indices.length === 0) return
      const label = indices.length === 1 ? '这条消息' : `选中的 ${indices.length} 条消息`
      if (!confirm(`确定删除${label}？`)) return
      try {
        await deleteMemoryMessages(indices, {
          relPath: scope.relPath,
          sessionId: scope.useLiveSession ? sessionId : undefined,
        })
        cancelSelection()
        await refreshAfterMessageDelete(scope)
      } catch (err) {
        setError(err instanceof Error ? err.message : '删除失败')
      }
    },
    [cancelSelection, refreshAfterMessageDelete, sessionId],
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

  const openDetail = async (item: MemoryItem) => {
    setSelected(item)
    setDetail('')
    try {
      const res = await fetchMemoryDetail(item.rel_path)
      setDetail(res.body)
    } catch (err) {
      setDetail(err instanceof Error ? err.message : '读取失败')
    }
  }

  const handleDelete = async (item: MemoryItem) => {
    if (!confirm(`删除「${item.title}」？此操作不可撤销。`)) return
    await deleteMemory(item.rel_path)
    void loadTab(tab)
    void loadSummary()
    setSelected(null)
  }

  const handleMark = async (item: MemoryItem) => {
    await toggleMemoryMark(item.rel_path)
    void loadTab(tab)
  }

  const handleClearChat = async () => {
    if (!confirm('清空当前会话的聊天上下文？')) return
    await clearChatSession(sessionId)
    setChat([])
  }

  const handleMaintenance = async (action: 'daily' | 'weekly' | 'monthly' | 'catchup') => {
    setMaintainLog('执行中…')
    try {
      const res = await runMemoryMaintenance(action, false)
      setMaintainLog(JSON.stringify(res.result, null, 2))
      void loadSummary()
      if (tab !== 'maintain') void loadTab(tab)
    } catch (err) {
      setMaintainLog(err instanceof Error ? err.message : '维护失败')
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            aria-label="关闭后台"
            className="fixed inset-0 z-[70] bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className={cn(
              'fixed bottom-0 right-0 z-[80] flex max-h-[min(88vh,720px)] w-full max-w-lg flex-col',
              'rounded-t-2xl border border-white/15 bg-[#12141a]/95 shadow-2xl backdrop-blur-xl',
            )}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
          >
            <header className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <h2 className="text-base font-medium text-foreground">{DEFAULT_CHARACTER_NAME} · 记忆宫殿</h2>
                <p className="mt-0.5 text-xs text-muted">
                  短 {counts.short ?? 0} · 中 {counts.medium ?? 0} · 长 {counts.long ?? 0}
                </p>
                <p className="mt-1 text-[10px] leading-relaxed text-muted/80">
                  点击消息可删除单条，或进入选择模式后批量删除。
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    void loadSummary()
                    void loadTab(tab)
                  }}
                  disabled={loading}
                  className="rounded-full border border-white/15 px-3 py-1 text-xs text-muted hover:text-foreground disabled:opacity-50"
                >
                  刷新
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-full border border-white/15 px-3 py-1 text-sm text-muted hover:text-foreground"
                >
                  关闭
                </button>
              </div>
            </header>

            <nav className="flex gap-1 overflow-x-auto border-b border-white/10 px-3 py-2">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTab(t.id)}
                  className={cn(
                    'shrink-0 rounded-full px-3 py-1.5 text-xs transition-colors',
                    tab === t.id
                      ? 'bg-white/15 text-foreground'
                      : 'text-muted hover:text-foreground',
                  )}
                >
                  {t.label}
                </button>
              ))}
            </nav>

            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
              {loading && <p className="text-sm text-muted">加载中…</p>}
              {error && <p className="text-sm text-red-300/90">{error}</p>}

              {!loading && tab === 'short' && (
                <ul className="space-y-4">
                  {shortSessions.length === 0 && !error && (
                    <p className="text-sm text-muted/80">暂无短期对话记忆</p>
                  )}
                  {shortSessions.map(({ item, messages }) => {
                    const scope = scopeForItem(item)
                    const inSelection = selectionScope?.id === scope.id
                    return (
                    <li
                      key={item.id}
                      className="overflow-hidden rounded-xl border border-white/10 bg-black/20"
                    >
                      <div className="flex items-center justify-between border-b border-white/10 px-3 py-2">
                        <span className="text-xs font-medium text-foreground/90">
                          {item.marked && '★ '}
                          {shortMemorySessionLabel(item)}
                        </span>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            className="text-[11px] text-muted hover:text-foreground"
                            onClick={() => void handleMark(item)}
                          >
                            {item.marked ? '取消标记' : '标记重要'}
                          </button>
                          <button
                            type="button"
                            className="text-[11px] text-red-300/80 hover:text-red-200"
                            onClick={() => void handleDelete(item)}
                          >
                            删除会话
                          </button>
                        </div>
                      </div>
                      <MemoryChatBubbles
                        messages={messages}
                        className="rounded-none"
                        interactive
                        selectionMode={inSelection}
                        selectedIndices={inSelection ? selectedIndices : undefined}
                        onMessageClick={(index) => handleMessageClick(scope, index)}
                      />
                    </li>
                    )
                  })}
                </ul>
              )}

              {!loading && tab !== 'chat' && tab !== 'maintain' && tab !== 'short' && (
                <ul className="space-y-2">
                  {items.length === 0 && !error && (
                    <p className="text-sm text-muted/80">暂无记忆条目</p>
                  )}
                  {items.map((item) => (
                    <li
                      key={item.id}
                      className={cn(
                        'rounded-xl border border-white/10 bg-white/5 p-3',
                        selected?.id === item.id && 'border-white/25',
                      )}
                    >
                      <button
                        type="button"
                        className="w-full text-left"
                        onClick={() => void openDetail(item)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-sm font-medium text-foreground">
                            {item.marked && '★ '}
                            {item.title}
                          </span>
                          <span className="shrink-0 text-[10px] text-muted">{item.category}</span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs text-muted">{item.preview}</p>
                      </button>
                      <div className="mt-2 flex gap-2">
                        <button
                          type="button"
                          className="text-[11px] text-muted hover:text-foreground"
                          onClick={() => void handleMark(item)}
                        >
                          {item.marked ? '取消标记' : '标记重要'}
                        </button>
                        <button
                          type="button"
                          className="text-[11px] text-red-300/80 hover:text-red-200"
                          onClick={() => void handleDelete(item)}
                        >
                          删除
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              {selected && detail && tab !== 'chat' && tab !== 'maintain' && tab !== 'short' && (
                <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3">
                  <p className="mb-2 text-xs text-muted">{selected.rel_path}</p>
                  <pre className="whitespace-pre-wrap text-xs leading-relaxed text-foreground/90">
                    {detail}
                  </pre>
                </div>
              )}

              {tab === 'chat' && !loading && (
                <div>
                  <div className="mb-3 flex justify-end">
                    <button
                      type="button"
                      onClick={() => void handleClearChat()}
                      className="rounded-full border border-white/15 px-3 py-1 text-xs text-muted hover:text-foreground"
                    >
                      清空会话上下文
                    </button>
                  </div>
                  <MemoryChatBubbles
                    messages={chat}
                    emptyText="当前无内存中的聊天记录"
                    interactive
                    selectionMode={selectionScope?.id === LIVE_CHAT_SCOPE_ID}
                    selectedIndices={
                      selectionScope?.id === LIVE_CHAT_SCOPE_ID ? selectedIndices : undefined
                    }
                    onMessageClick={(index) => handleMessageClick(liveChatScope, index)}
                  />
                </div>
              )}

              {tab === 'maintain' && (
                <div className="space-y-3">
                  <p className="text-xs leading-relaxed text-muted">
                    按百事通记忆模块：日结汇总短期 → 中期；周结/月结 rollup 到长期并归档清理旧文件。
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(['daily', 'weekly', 'monthly', 'catchup'] as const).map((action) => (
                      <button
                        key={action}
                        type="button"
                        onClick={() => void handleMaintenance(action)}
                        className="rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-foreground hover:bg-white/10"
                      >
                        {action === 'daily' && '日结清洗'}
                        {action === 'weekly' && '周结归档'}
                        {action === 'monthly' && '月结归档'}
                        {action === 'catchup' && '补跑全部'}
                      </button>
                    ))}
                  </div>
                  {maintainLog && (
                    <pre className="max-h-48 overflow-auto rounded-lg bg-black/30 p-3 text-[10px] text-muted">
                      {maintainLog}
                    </pre>
                  )}
                </div>
              )}
            </div>

            {selectionScope && (
              <div className="flex items-center justify-between gap-2 border-t border-white/10 bg-[#1a1d26]/95 px-4 py-3">
                <span className="text-xs text-muted">已选 {selectedIndices.size} 条</span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={cancelSelection}
                    className="rounded-full border border-white/15 px-3 py-1.5 text-xs text-muted"
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    disabled={selectedIndices.size === 0}
                    onClick={() =>
                      void handleDeleteMessages(selectionScope, Array.from(selectedIndices).sort())
                    }
                    className="rounded-full bg-red-500/20 px-3 py-1.5 text-xs text-red-300 disabled:opacity-40"
                  >
                    删除选中
                  </button>
                </div>
              </div>
            )}
          </motion.aside>

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
      )}
    </AnimatePresence>
  )
}
