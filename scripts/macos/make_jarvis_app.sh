#!/usr/bin/env bash
# 构建真正的「贾维斯.app」—— 系统权限列表显示「贾维斯」（非 Terminal/Python）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

log() { printf '\033[1;36m[jarvis-app]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[jarvis-app]\033[0m %s\n' "$*" >&2; }

if [[ "$(uname -s)" != "Darwin" ]]; then
  err "仅支持 macOS"
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

log "安装 Python 依赖…"
pip install -q -r requirements.txt
pip install -q py2app

log "构建前端 PWA…"
npm run build

log "生成 App 图标…"
bash scripts/macos/generate_app_icon.sh

log "打包 贾维斯.app（alias 模式，依赖项目 .venv）…"
# 清理旧产物（保留 npm 的 dist/ 前端目录）
rm -rf build dist/贾维斯.app dist/贾维斯

python scripts/macos/setup_py2app_alias.py py2app

APP_PATH=""
if [[ -d "dist/贾维斯.app" ]]; then
  APP_PATH="dist/贾维斯.app"
elif [[ -d "dist/Jarvis.app" ]]; then
  mv "dist/Jarvis.app" "dist/贾维斯.app"
  APP_PATH="dist/贾维斯.app"
else
  err "未找到打包产物，请检查 py2app 输出"
  ls -la dist/ || true
  exit 1
fi

# 项目资源（.env / data / venv）放在 App 内，便于独立运行
RES="$APP_PATH/Contents/Resources"
mkdir -p "$RES/project"
ln -sfn "$ROOT/.env" "$RES/project/.env" 2>/dev/null || cp -n "$ROOT/.env.example" "$RES/project/.env" 2>/dev/null || true
ln -sfn "$ROOT/data" "$RES/project/data" 2>/dev/null || true
ln -sfn "$ROOT/dist" "$RES/project/dist" 2>/dev/null || true
ln -sfn "$ROOT/neuralpal" "$RES/project/neuralpal" 2>/dev/null || true
ln -sfn "$ROOT/server" "$RES/project/server" 2>/dev/null || true
ln -sfn "$ROOT/.venv" "$RES/project/.venv" 2>/dev/null || true

log "安装到「应用程序」与桌面…"
bash scripts/macos/install_jarvis_app.sh

log "稳定代码签名（避免辅助功能 cdhash 失效）…"
bash scripts/macos/sign_jarvis_app.sh "$ROOT/$APP_PATH" || log "签名跳过（可稍后运行 ./scripts/macos/sign_jarvis_app.sh）"

log "✓ 已生成 $ROOT/$APP_PATH"
log ""
log "【重要】代操权限请授权给「贾维斯」，不是 Terminal / Python："
log "  1. 从启动台或桌面打开「贾维斯」"
log "  2. 系统设置 → 隐私与安全性 → 辅助功能 / 屏幕录制"
log "  3. 打开「贾维斯」开关"
log ""
log "开发调试仍可用 ./scripts/run_jarvis.sh（权限会显示 Python，仅供开发）"
