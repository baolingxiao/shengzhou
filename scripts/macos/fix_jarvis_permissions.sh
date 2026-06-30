#!/usr/bin/env bash
# 修复 Sequoia 上「系统设置开关 ON 但贾维斯检测未授权」的 TCC 陈旧记录问题。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="/Applications/贾维斯.app"

log() { printf '\033[1;36m[jarvis-fix-perms]\033[0m %s\n' "$*"; }

log "1/4 结束正在运行的贾维斯…"
kill $(lsof -ti :8766 2>/dev/null) 2>/dev/null || true
sleep 1

log "2/4 重置 TCC 授权记录…"
tccutil reset Accessibility com.neuralpal.jarvis 2>/dev/null || true
tccutil reset ScreenCapture com.neuralpal.jarvis 2>/dev/null || true

log "3/4 重新签署 App（稳定证书 + entitlements）…"
JARVIS_RESET_TCC=0 bash "$ROOT/scripts/macos/sign_jarvis_app.sh" "$APP"

log "4/4 打开系统设置（请手动 − 删除旧条目，+ 添加 $APP）…"
open "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility" || true
open "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_ScreenCapture" || true

log ""
log "请完成："
log "  · 辅助功能 / 录屏：先 − 删除「贾维斯」，再 + 选择 $APP"
log "  · 系统设置 → 隐私与安全性 → 开发者模式：若存在请打开（Sequoia 本地开发 App 可能需要）"
log "  · ⌘Q 退出后从启动台重新打开贾维斯 → 点「重新检测」"
