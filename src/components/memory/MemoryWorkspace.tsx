import type { ReactNode } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { cn } from '../../lib/cn'
import { DEFAULT_CHARACTER_NAME } from '../../lib/characterConfig'
import { MemorySidebar, type MemoryTabId } from './MemorySidebar'
import { MemoryList } from './MemoryList'
import { MemoryDetailPane } from './MemoryDetailPane'
import type { MemoryItem } from '../../lib/adminApi'
import type { ChatHistoryMessage } from '../../lib/adminApi'

type MemoryWorkspaceProps = {
  open: boolean
  onClose: () => void
  tab: MemoryTabId
  onTabChange: (tab: MemoryTabId) => void
  counts: Record<string, number>
  loading?: boolean
  error?: string | null
  filters?: ReactNode
  listItems?: MemoryItem[]
  listEmptyText?: string
  shortList?: boolean
  selectedItem?: MemoryItem | null
  onSelectItem?: (item: MemoryItem) => void
  onMarkItem?: (item: MemoryItem) => void
  onDeleteItem?: (item: MemoryItem) => void
  detailMemoryId?: string
  detailTitle?: string
  detailBody?: string
  detailMessages?: ChatHistoryMessage[]
  detailLoading?: boolean
  detailInteractive?: boolean
  selectionMode?: boolean
  selectedIndices?: Set<number>
  onMessageClick?: (index: number) => void
  onRefresh?: () => void
  centerContent?: ReactNode
  rightContent?: ReactNode
  selectionBar?: ReactNode
  mobileDetailOpen?: boolean
  onMobileDetailClose?: () => void
}

export function MemoryWorkspace({
  open,
  onClose,
  tab,
  onTabChange,
  counts,
  loading,
  error,
  filters,
  listItems = [],
  listEmptyText,
  shortList,
  selectedItem,
  onSelectItem,
  onMarkItem,
  onDeleteItem,
  detailMemoryId,
  detailTitle,
  detailBody,
  detailMessages,
  detailLoading,
  detailInteractive,
  selectionMode,
  selectedIndices,
  onMessageClick,
  onRefresh,
  centerContent,
  rightContent,
  selectionBar,
  mobileDetailOpen,
  onMobileDetailClose,
}: MemoryWorkspaceProps) {
  const showListColumn = tab !== 'transparency' && tab !== 'maintain'
  const showDetailColumn = showListColumn && (detailMemoryId || detailLoading)

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            aria-label="关闭记忆宫殿"
            className="fixed inset-0 z-[70] bg-black/55 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className={cn(
              'fixed inset-x-0 bottom-0 z-[80] flex max-h-[min(92vh,820px)] flex-col',
              'border border-jarvis-border bg-jarvis-bg/95 shadow-2xl backdrop-blur-xl',
              'lg:inset-x-auto lg:right-4 lg:top-4 lg:bottom-4 lg:left-auto lg:max-h-none lg:w-[min(1120px,calc(100vw-2rem))] lg:rounded-jarvis-lg',
            )}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
          >
            <header className="flex shrink-0 items-center justify-between border-b border-jarvis-border px-4 py-3 lg:px-5">
              <div>
                <h2 className="text-base font-medium text-jarvis-text">
                  {DEFAULT_CHARACTER_NAME} · Memory Space
                </h2>
                <p className="mt-0.5 text-[11px] text-jarvis-text-muted">
                  点击消息可删除单条，或进入选择模式批量删除
                </p>
              </div>
              <div className="flex items-center gap-2">
                {onRefresh && (
                  <button
                    type="button"
                    onClick={onRefresh}
                    disabled={loading}
                    className="rounded-jarvis-sm border border-jarvis-border px-3 py-1 text-xs text-jarvis-text-muted hover:text-jarvis-text disabled:opacity-50"
                  >
                    刷新
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-jarvis-sm border border-jarvis-border px-3 py-1 text-xs text-jarvis-text-muted hover:text-jarvis-text"
                >
                  关闭
                </button>
              </div>
            </header>

            <div className="flex min-h-0 flex-1 flex-col lg:grid lg:grid-cols-[188px_1fr_1.15fr]">
              <MemorySidebar
                tab={tab}
                onTabChange={onTabChange}
                counts={counts}
                filters={filters}
                className="hidden lg:flex"
              />

              <nav className="flex shrink-0 gap-1 overflow-x-auto border-b border-jarvis-border px-3 py-2 lg:hidden">
                {(['short', 'medium', 'long', 'transparency', 'maintain'] as MemoryTabId[]).map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => onTabChange(id)}
                    className={cn(
                      'shrink-0 rounded-full px-3 py-1.5 text-xs transition-colors',
                      tab === id
                        ? 'bg-jarvis-accent-soft text-jarvis-accent'
                        : 'text-jarvis-text-muted hover:text-jarvis-text',
                    )}
                  >
                    {id === 'short' && '当前'}
                    {id === 'medium' && '周期'}
                    {id === 'long' && '长期'}
                    {id === 'transparency' && '引用'}
                    {id === 'maintain' && '维护'}
                  </button>
                ))}
              </nav>

              {showListColumn && (
                <div
                  className={cn(
                    'min-h-0 overflow-y-auto border-jarvis-border p-3 lg:border-r',
                    showDetailColumn && mobileDetailOpen ? 'hidden lg:block' : 'flex-1 lg:flex-none',
                  )}
                >
                  {filters && (
                    <div className="mb-3 lg:hidden">{filters}</div>
                  )}
                  {loading && <p className="text-sm text-jarvis-text-muted">加载中…</p>}
                  {error && <p className="mb-2 text-sm text-jarvis-red">{error}</p>}
                  {!loading && centerContent}
                  {!loading && !centerContent && onSelectItem && (
                    <MemoryList
                      items={listItems}
                      selectedId={selectedItem?.id}
                      shortLabels={shortList}
                      emptyText={listEmptyText}
                      onSelect={onSelectItem}
                      onMark={onMarkItem}
                      onDelete={onDeleteItem}
                    />
                  )}
                </div>
              )}

              {(tab === 'transparency' || tab === 'maintain') && (
                <div className="min-h-0 flex-1 overflow-y-auto p-4 lg:col-span-2">
                  {loading && <p className="text-sm text-jarvis-text-muted">加载中…</p>}
                  {error && <p className="mb-2 text-sm text-jarvis-red">{error}</p>}
                  {!loading && rightContent}
                </div>
              )}

              {showListColumn && (
                <div
                  className={cn(
                    'min-h-0 overflow-hidden border-jarvis-border lg:border-l',
                    mobileDetailOpen ? 'flex flex-1 flex-col' : 'hidden lg:flex lg:flex-col',
                  )}
                >
                  {mobileDetailOpen && onMobileDetailClose && (
                    <div className="flex shrink-0 items-center border-b border-jarvis-border px-3 py-2 lg:hidden">
                      <button
                        type="button"
                        onClick={onMobileDetailClose}
                        className="text-xs text-jarvis-accent"
                      >
                        ← 返回列表
                      </button>
                    </div>
                  )}
                  {rightContent ?? (
                    <MemoryDetailPane
                      memoryId={detailMemoryId}
                      title={detailTitle}
                      body={detailBody}
                      messages={detailMessages}
                      loading={detailLoading}
                      interactiveBubbles={detailInteractive}
                      selectionMode={selectionMode}
                      selectedIndices={selectedIndices}
                      onMessageClick={onMessageClick}
                    />
                  )}
                </div>
              )}
            </div>

            {selectionBar}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
