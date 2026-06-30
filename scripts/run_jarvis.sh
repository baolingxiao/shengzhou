#!/usr/bin/env bash
# 贾维斯 · 一键启动（后端 API + 前端 PWA）
#
# 用法:
#   ./scripts/run_jarvis.sh              # 开发模式（默认）
#   ./scripts/run_jarvis.sh dev
#   ./scripts/run_jarvis.sh prod         # 构建后用 preview 提供 PWA（更接近桌面安装）
#   ./scripts/run_jarvis.sh install      # 仅安装 Python / Node 依赖
#   ./scripts/run_jarvis.sh stop         # 停止后台进程
#
# 环境变量:
#   NEURALPAL_BACKEND_PORT   后端端口（默认 8766）
#   NEURALPAL_FRONTEND_PORT  前端端口（默认 5190）
#   JARVIS_SKIP_INSTALL=1    跳过 pip/npm install
#   JARVIS_OPEN_BROWSER=1    启动后打开浏览器（macOS）

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:-dev}"
BACKEND_PORT="${NEURALPAL_BACKEND_PORT:-8766}"
FRONTEND_PORT="${NEURALPAL_FRONTEND_PORT:-5190}"
RUN_DIR="$ROOT/data/run"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"

mkdir -p "$RUN_DIR"

log() {
  printf '\033[1;36m[jarvis]\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33m[jarvis]\033[0m %s\n' "$*" >&2
}

err() {
  printf '\033[1;31m[jarvis]\033[0m %s\n' "$*" >&2
}

port_pid() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1 || true
}

kill_port() {
  local port="$1"
  local pid
  pid="$(port_pid "$port")"
  if [[ -n "$pid" ]]; then
    log "释放端口 $port（PID $pid）..."
    kill "$pid" 2>/dev/null || true
    sleep 0.4
  fi
}

stop_all() {
  log "正在停止贾维斯..."
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    local bp
    bp="$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)"
    if [[ -n "$bp" ]] && kill -0 "$bp" 2>/dev/null; then
      kill "$bp" 2>/dev/null || true
    fi
    rm -f "$BACKEND_PID_FILE"
  fi
  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    local fp
    fp="$(cat "$FRONTEND_PID_FILE" 2>/dev/null || true)"
    if [[ -n "$fp" ]] && kill -0 "$fp" 2>/dev/null; then
      kill "$fp" 2>/dev/null || true
    fi
    rm -f "$FRONTEND_PID_FILE"
  fi
  kill_port "$BACKEND_PORT"
  kill_port "$FRONTEND_PORT"
}

ensure_env() {
  if [[ ! -f "$ROOT/.env" ]]; then
    warn "未找到 .env，请复制 .env.example 并填写 API 密钥："
    warn "  cp .env.example .env"
    if [[ -f "$ROOT/.env.example" ]]; then
      cp "$ROOT/.env.example" "$ROOT/.env"
      warn "已自动从 .env.example 生成 .env，请编辑后重新运行。"
      exit 1
    fi
  fi
  # 不在 shell 中 source .env（路径含空格会报错；含特殊字符也不安全）。
  # Python 后端通过 pydantic-settings / python-dotenv 读取 .env。
}

install_deps() {
  if [[ "${JARVIS_SKIP_INSTALL:-0}" == "1" ]]; then
    log "跳过依赖安装（JARVIS_SKIP_INSTALL=1）"
    return 0
  fi

  log "检查 Python 虚拟环境..."
  if [[ ! -d "$ROOT/.venv" ]]; then
    python3 -m venv "$ROOT/.venv"
  fi
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  pip install -q -r "$ROOT/requirements.txt"

  log "检查 Node 依赖..."
  if [[ ! -d "$ROOT/node_modules" ]]; then
    npm install
  fi
}

start_backend() {
  kill_port "$BACKEND_PORT"
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  log "启动后端 API → 127.0.0.1:$BACKEND_PORT"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    warn "开发模式：系统权限会显示 Terminal/Python，无法授权「贾维斯」。"
    warn "正式使用请运行 ./scripts/macos/make_jarvis_app.sh 后双击 dist/贾维斯.app"
  fi
  (
    cd "$ROOT"
    export NEURALPAL_BACKEND_PORT="$BACKEND_PORT"
    exec python -m server.main
  ) >>"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
  local waited=0
  while ! curl -sf "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null 2>&1; do
    sleep 0.3
    waited=$((waited + 1))
    if [[ $waited -gt 40 ]]; then
      err "后端启动超时，查看日志: $BACKEND_LOG"
      tail -20 "$BACKEND_LOG" >&2 || true
      stop_all
      exit 1
    fi
    if ! kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
      err "后端进程已退出，查看日志: $BACKEND_LOG"
      tail -30 "$BACKEND_LOG" >&2 || true
      exit 1
    fi
  done
  log "后端就绪 ✓  http://127.0.0.1:$BACKEND_PORT/api/health"
}

open_browser() {
  if [[ "${JARVIS_OPEN_BROWSER:-0}" != "1" ]]; then
    return 0
  fi
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:$FRONTEND_PORT"
  fi
}

print_banner() {
  local mode_label="$1"
  cat <<EOF

  ╔══════════════════════════════════════════════╗
  ║  贾维斯 · Neural Pal  ($mode_label)
  ╠══════════════════════════════════════════════╣
  ║  前端 PWA   http://127.0.0.1:$FRONTEND_PORT
  ║  后端 API   http://127.0.0.1:$BACKEND_PORT
  ║  默认登录   admin / jarvis
  ╠══════════════════════════════════════════════╣
  ║  安装到程序坞: 浏览器 → 安装应用 / 添加到程序坞
  ║  停止服务:     ./scripts/run_jarvis.sh stop
  ╚══════════════════════════════════════════════╝

EOF
}

cleanup_on_exit() {
  local code=$?
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    local bp
    bp="$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)"
    if [[ -n "$bp" ]] && kill -0 "$bp" 2>/dev/null; then
      kill "$bp" 2>/dev/null || true
    fi
    rm -f "$BACKEND_PID_FILE"
  fi
  rm -f "$FRONTEND_PID_FILE"
  exit "$code"
}

run_dev() {
  ensure_env
  install_deps
  start_backend
  trap cleanup_on_exit INT TERM EXIT
  print_banner "开发 dev"
  print_app_hint
  open_browser
  log "启动前端开发服务器（Ctrl+C 停止全部）..."
  export NEURALPAL_FRONTEND_PORT="$FRONTEND_PORT"
  npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
}

run_prod() {
  ensure_env
  install_deps
  log "构建前端 PWA..."
  npm run build
  start_backend
  trap cleanup_on_exit INT TERM EXIT
  print_banner "生产 preview"
  print_app_hint
  open_browser
  log "启动 PWA preview（Ctrl+C 停止全部）..."
  npm run preview -- --host 127.0.0.1 --port "$FRONTEND_PORT"
}

print_app_hint() {
  if [[ -d "$ROOT/dist/贾维斯.app" ]]; then
    log "桌面 App：$ROOT/dist/贾维斯.app"
  else
    log "生成桌面 App：./scripts/macos/make_jarvis_app.sh（推荐给最终用户）"
  fi
}

case "$MODE" in
  stop)
    stop_all
    log "已停止。"
    ;;
  install)
    install_deps
    log "依赖安装完成。"
    ;;
  prod|production|preview)
    run_prod
    ;;
  dev|start|"")
    run_dev
    ;;
  -h|--help|help)
    sed -n '2,15p' "$0" | sed 's/^# \?//'
    ;;
  *)
    err "未知模式: $MODE（可用 dev | prod | install | stop）"
    exit 1
    ;;
esac
