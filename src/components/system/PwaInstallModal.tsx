import { SystemModal, ModalActions } from './SystemModal'
import type { PwaInstallMode } from '../../hooks/usePwaInstall'

type PwaInstallModalProps = {
  open: boolean
  mode: PwaInstallMode
  installing: boolean
  onInstall: () => void | Promise<void>
  onDismiss: () => void
}

export function PwaInstallModal({
  open,
  mode,
  installing,
  onInstall,
  onDismiss,
}: PwaInstallModalProps) {
  const native = mode === 'native'

  return (
    <SystemModal open={open} title="安装贾维斯到本机">
      {native ? (
        <>
          <p>
            将「贾维斯 · 沈昼」安装为桌面应用后，可从程序坞 / 主屏幕直接打开，无需每次输入网址。
          </p>
          <p className="text-white/65">
            以后界面更新会在应用内弹窗提示，点「立即更新」即可，无需重新安装。
          </p>
        </>
      ) : mode === 'safari_ios' ? (
        <>
          <p>Safari 请按以下步骤安装到主屏幕：</p>
          <ol className="list-decimal space-y-1 pl-5 text-white/80">
            <li>点底部 <strong>分享</strong> 按钮</li>
            <li>选择 <strong>添加到主屏幕</strong></li>
            <li>点 <strong>添加</strong></li>
          </ol>
          <p className="text-white/65">安装后请从主屏幕图标打开，以获得完整体验与更新提醒。</p>
        </>
      ) : mode === 'safari_mac' ? (
        <>
          <p>Mac 版 Safari 请按以下步骤安装：</p>
          <ol className="list-decimal space-y-1 pl-5 text-white/80">
            <li>点菜单栏 <strong>文件</strong></li>
            <li>选择 <strong>添加到程序坞</strong>（或地址栏旁的分享 → 添加到程序坞）</li>
          </ol>
          <p className="text-white/65">安装后从程序坞打开；有 UI 更新时应用内会提示。</p>
        </>
      ) : mode === 'chrome_manual' ? (
        <>
          <p>请使用 Chrome / Edge 将贾维斯安装到本机：</p>
          <ol className="list-decimal space-y-1 pl-5 text-white/80">
            <li>点地址栏右侧的 <strong>安装</strong> 或 <strong>⊕</strong> 图标</li>
            <li>在弹窗中确认 <strong>安装</strong></li>
          </ol>
          <p className="text-white/65">若未看到图标，请刷新页面后再试，或先多使用片刻后重开。</p>
        </>
      ) : (
        <p className="text-white/65">当前浏览器暂不支持一键安装，请使用 Chrome / Edge 打开本页，或换用 Safari 按指引添加。</p>
      )}

      <ModalActions
        primaryLabel={native ? '立即安装' : '我知道了'}
        secondaryLabel="稍后再说"
        onPrimary={() => void (native ? onInstall() : onDismiss())}
        onSecondary={onDismiss}
        primaryLoading={installing}
      />
    </SystemModal>
  )
}
