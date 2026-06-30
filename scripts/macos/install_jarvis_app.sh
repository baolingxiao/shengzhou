#!/usr/bin/env bash
# 将 dist/贾维斯.app 安装到「应用程序」并创建桌面快捷方式（启动台会索引 /Applications）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/dist/贾维斯.app"
DEST="/Applications/贾维斯.app"
DESKTOP_LINK="$HOME/Desktop/贾维斯.app"

log() { printf '\033[1;36m[jarvis-install]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[jarvis-install]\033[0m %s\n' "$*" >&2; }

if [[ "$(uname -s)" != "Darwin" ]]; then
  err "仅支持 macOS"
  exit 1
fi

if [[ ! -d "$SRC" ]]; then
  err "未找到 $SRC"
  err "请先运行: ./scripts/macos/make_jarvis_app.sh"
  exit 1
fi

log "安装到 $DEST …"
if [[ -d "$DEST" ]]; then
  rm -rf "$DEST"
fi
ditto "$SRC" "$DEST"

log "创建桌面快捷方式 → $DESKTOP_LINK"
ln -sfn "$DEST" "$DESKTOP_LINK"

log "✓ 已安装"
log "  · 启动台：在「应用程序」中搜索「贾维斯」（若未出现可注销后重登）"
log "  · 桌面：已放置快捷方式 $DESKTOP_LINK"
log "  · 直接打开：open -a \"$DEST\""

open -R "$DEST"
