import { useState } from 'react'
import { SystemModal, ModalActions } from './SystemModal'
import type { UpdateCheckResult } from '../../lib/systemApi'

type UpdatePromptModalProps = {
  open: boolean
  swUpdateReady: boolean
  backendUpdateReady: boolean
  updateInfo: UpdateCheckResult | null
  applying: boolean
  onConfirm: () => void | Promise<void>
  onDismiss: () => void | Promise<void>
}

export function UpdatePromptModal({
  open,
  swUpdateReady,
  backendUpdateReady,
  updateInfo,
  applying,
  onConfirm,
  onDismiss,
}: UpdatePromptModalProps) {
  const [error, setError] = useState('')

  const handleConfirm = async () => {
    setError('')
    try {
      await onConfirm()
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败')
    }
  }

  const parts: string[] = []
  if (swUpdateReady) parts.push('前端界面有新版本（PWA）')
  if (backendUpdateReady) parts.push('应用代码有更新（Git）')

  return (
    <SystemModal open={open} title="发现新版本">
      <p>
        {parts.join('；') || '贾维斯有新版本可用'}。是否现在更新？
      </p>
      <p className="text-white/65">
        选择「稍后」将保持当前版本，不会自动重启或刷新，直到你下次确认。
      </p>
      {updateInfo && backendUpdateReady && (
        <div className="rounded-2xl border border-white/15 bg-black/20 p-3 text-xs leading-relaxed">
          <p>
            当前：<code>{updateInfo.build_id}</code>
          </p>
          {updateInfo.commits_behind > 0 && (
            <p className="mt-1">落后远程 {updateInfo.commits_behind} 个提交</p>
          )}
          {updateInfo.summary && (
            <pre className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap text-white/70">
              {updateInfo.summary}
            </pre>
          )}
        </div>
      )}
      {error && <p className="text-red-200/90">{error}</p>}
      <ModalActions
        primaryLabel="立即更新"
        secondaryLabel="稍后"
        onPrimary={() => void handleConfirm()}
        onSecondary={() => void onDismiss()}
        primaryLoading={applying}
      />
    </SystemModal>
  )
}
