import { useCallback, useMemo, useState } from 'react'
import { UpdatePromptModal } from './UpdatePromptModal'
import { PwaInstallModal } from './PwaInstallModal'
import { MacPermissionsModal } from './MacPermissionsModal'
import { usePwaUpdate } from '../../hooks/usePwaUpdate'
import { usePwaInstall } from '../../hooks/usePwaInstall'
import { useBackendUpdate } from '../../hooks/useBackendUpdate'
import { useMacPermissionsContext } from '../../contexts/MacPermissionsContext'
import { useUserSession } from '../../contexts/UserSessionContext'
import { MacPermissionsStatusPanel } from './MacPermissionsStatusPanel'
import { isPwaChannel } from '../../lib/pwaChannel'

/**
 * PWA / 桌面渠道：安装引导 + 更新确认弹窗 + Mac 代操权限提醒
 */
export function SystemModalsShell() {
  const pwaChannel = isPwaChannel()
  const session = useUserSession()
  const pwa = usePwaUpdate()
  const pwaInstall = usePwaInstall(Boolean(session.username))
  const backend = useBackendUpdate(true)
  const perms = useMacPermissionsContext()
  const [updateBusy, setUpdateBusy] = useState(false)

  const updateOpen = useMemo(
    () => pwa.swUpdateReady || backend.backendUpdateReady,
    [pwa.swUpdateReady, backend.backendUpdateReady],
  )

  const installOpen = useMemo(
    () => pwaInstall.shouldPrompt && !updateOpen && !perms.shouldPrompt,
    [pwaInstall.shouldPrompt, updateOpen, perms.shouldPrompt],
  )

  const handleUpdateConfirm = useCallback(async () => {
    setUpdateBusy(true)
    try {
      if (backend.backendUpdateReady) {
        const result = await backend.applyBackendUpdate()
        if (!result.ok) throw new Error(result.message)
      }
      if (pwa.swUpdateReady) {
        await pwa.applySwUpdate()
      }
    } finally {
      setUpdateBusy(false)
    }
  }, [backend, pwa])

  const handleUpdateDismiss = useCallback(async () => {
    if (backend.backendUpdateReady) {
      await backend.dismissBackendUpdate()
    }
    if (pwa.swUpdateReady) {
      pwa.dismissSwUpdate()
    }
  }, [backend, pwa])

  return (
    <>
      <PwaInstallModal
        open={installOpen}
        mode={pwaInstall.mode}
        installing={pwaInstall.installing}
        onInstall={pwaInstall.applyInstall}
        onDismiss={pwaInstall.dismissInstall}
      />
      <UpdatePromptModal
        open={updateOpen}
        swUpdateReady={pwa.swUpdateReady}
        backendUpdateReady={backend.backendUpdateReady}
        updateInfo={backend.info}
        applying={updateBusy || pwa.applying || backend.applying}
        onConfirm={handleUpdateConfirm}
        onDismiss={handleUpdateDismiss}
      />
      <MacPermissionsModal
        open={perms.shouldPrompt}
        snapshot={perms.snapshot}
        rechecking={perms.rechecking}
        autoSettingUp={perms.autoSettingUp}
        recheckFeedback={perms.recheckFeedback}
        showSuccessCelebration={perms.showSuccessCelebration}
        onAutoSetup={() => void perms.runAutoSetup()}
        onDismiss={perms.dismissReminder}
      />
      <MacPermissionsStatusPanel />
      {pwaChannel && import.meta.env.DEV && (
        <div className="pointer-events-none fixed bottom-2 right-2 z-50 rounded-full bg-black/40 px-2 py-0.5 text-[10px] text-white/50">
          PWA · v{typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '?'}
        </div>
      )}
    </>
  )
}
