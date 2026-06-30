#!/usr/bin/env bash
# 用户确认更新后：拉代码、构建前端、重启后端（供 PWA / 桌面渠道）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[jarvis-update] restarting backend..."
exec "$ROOT/scripts/run_backend.sh"
