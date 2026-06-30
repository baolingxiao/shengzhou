#!/usr/bin/env bash
# 贾维斯 · 云端中心机部署（方案 B）
#
# 用法:
#   首次安装:  sudo bash scripts/deploy_server.sh install
#   发版更新:  sudo bash scripts/deploy_server.sh update
#   查看状态:  sudo bash scripts/deploy_server.sh status
#
# 默认仓库与安装路径（可按需覆盖环境变量）:
#   JARVIS_GIT_REPO=https://github.com/baolingxiao/shengzhou.git
#   JARVIS_INSTALL_DIR=/opt/jarvis
#   JARVIS_SERVICE_USER=jarvis

set -euo pipefail

JARVIS_GIT_REPO="${JARVIS_GIT_REPO:-https://github.com/baolingxiao/shengzhou.git}"
JARVIS_INSTALL_DIR="${JARVIS_INSTALL_DIR:-/opt/jarvis}"
JARVIS_SERVICE_USER="${JARVIS_SERVICE_USER:-jarvis}"
JARVIS_BRANCH="${JARVIS_BRANCH:-main}"
JARVIS_PORT="${NEURALPAL_BACKEND_PORT:-8766}"

log() { printf '\033[1;36m[jarvis-deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[jarvis-deploy]\033[0m %s\n' "$*" >&2; }
err() { printf '\033[1;31m[jarvis-deploy]\033[0m %s\n' "$*" >&2; }

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    err "请使用 root 或 sudo 运行: sudo bash $0 $*"
    exit 1
  fi
}

install_system_deps() {
  log "安装系统依赖…"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq \
    git curl ca-certificates \
    python3 python3-venv python3-pip \
    build-essential ffmpeg \
    nginx certbot python3-certbot-nginx

  if ! command -v node >/dev/null 2>&1 || [[ "$(node -v 2>/dev/null || echo v0)" < "v18" ]]; then
    log "安装 Node.js 20…"
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
  fi
}

ensure_service_user() {
  if ! id "$JARVIS_SERVICE_USER" &>/dev/null; then
    log "创建系统用户 $JARVIS_SERVICE_USER …"
    useradd --system --home "$JARVIS_INSTALL_DIR" --shell /usr/sbin/nologin "$JARVIS_SERVICE_USER"
  fi
}

clone_or_pull() {
  if [[ -d "$JARVIS_INSTALL_DIR/.git" ]]; then
    log "拉取最新代码 $JARVIS_GIT_REPO ($JARVIS_BRANCH) …"
    sudo -u "$JARVIS_SERVICE_USER" git -C "$JARVIS_INSTALL_DIR" fetch origin "$JARVIS_BRANCH"
    sudo -u "$JARVIS_SERVICE_USER" git -C "$JARVIS_INSTALL_DIR" checkout "$JARVIS_BRANCH"
    sudo -u "$JARVIS_SERVICE_USER" git -C "$JARVIS_INSTALL_DIR" pull origin "$JARVIS_BRANCH"
  else
    log "克隆仓库 $JARVIS_GIT_REPO → $JARVIS_INSTALL_DIR …"
    mkdir -p "$(dirname "$JARVIS_INSTALL_DIR")"
    git clone --branch "$JARVIS_BRANCH" "$JARVIS_GIT_REPO" "$JARVIS_INSTALL_DIR"
    chown -R "$JARVIS_SERVICE_USER:$JARVIS_SERVICE_USER" "$JARVIS_INSTALL_DIR"
  fi
}

ensure_env_file() {
  local env_file="$JARVIS_INSTALL_DIR/.env"
  if [[ ! -f "$env_file" ]]; then
    log "从 .env.example 创建 .env（请随后编辑 API 密钥与密码）…"
    cp "$JARVIS_INSTALL_DIR/.env.example" "$env_file"
    chown "$JARVIS_SERVICE_USER:$JARVIS_SERVICE_USER" "$env_file"
    chmod 600 "$env_file"

    # 云端默认配置
    cat >>"$env_file" <<'EOF'

# --- 由 deploy_server.sh 自动追加的云端配置 ---
JARVIS_APP_MODE=1
NEURALPAL_BIND=0.0.0.0
NEURALPAL_DESKTOP_UPDATE_CHECK_ENABLED=false
NEURALPAL_AGENT_ENABLED=false
NEURALPAL_VOICE_STT_PROVIDER=openai
EOF
    warn "请编辑 $env_file 填写 DOUBAO_API_KEY、JARVIS_AUTH_PASSWORD 等密钥后重新运行 update"
  fi
}

install_python_deps() {
  log "安装 Python 依赖…"
  sudo -u "$JARVIS_SERVICE_USER" bash -lc "
    cd '$JARVIS_INSTALL_DIR'
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
  "
}

build_frontend() {
  log "构建前端 PWA…"
  sudo -u "$JARVIS_SERVICE_USER" bash -lc "
    cd '$JARVIS_INSTALL_DIR'
    npm ci
    npm run build
  "
}

install_systemd_unit() {
  log "安装 systemd 服务…"
  sed \
    -e "s|@INSTALL_DIR@|$JARVIS_INSTALL_DIR|g" \
    -e "s|@SERVICE_USER@|$JARVIS_SERVICE_USER|g" \
    "$JARVIS_INSTALL_DIR/scripts/jarvis.service" >/etc/systemd/system/jarvis.service
  systemctl daemon-reload
  systemctl enable jarvis
}

start_service() {
  log "启动 / 重启贾维斯服务…"
  systemctl restart jarvis
  sleep 2
  if systemctl is-active --quiet jarvis; then
    log "服务运行中 ✓  http://127.0.0.1:$JARVIS_PORT/api/health"
  else
    err "服务启动失败，查看日志: journalctl -u jarvis -n 50 --no-pager"
    exit 1
  fi
}

print_next_steps() {
  cat <<EOF

  ╔══════════════════════════════════════════════════════════════╗
  ║  贾维斯云端部署完成
  ╠══════════════════════════════════════════════════════════════╣
  ║  仓库:     $JARVIS_GIT_REPO
  ║  目录:     $JARVIS_INSTALL_DIR
  ║  健康检查: curl http://127.0.0.1:$JARVIS_PORT/api/health
  ╠══════════════════════════════════════════════════════════════╣
  ║  下一步:
  ║  1. 编辑 $JARVIS_INSTALL_DIR/.env 填写 API 密钥
  ║  2. 配置 Nginx HTTPS（示例见 scripts/nginx-jarvis.conf）
  ║  3. 发版: sudo bash scripts/deploy_server.sh update
  ╚══════════════════════════════════════════════════════════════╝

EOF
}

cmd_install() {
  require_root install
  install_system_deps
  ensure_service_user
  clone_or_pull
  ensure_env_file
  install_python_deps
  build_frontend
  install_systemd_unit
  start_service
  print_next_steps
}

cmd_update() {
  require_root update
  if [[ ! -d "$JARVIS_INSTALL_DIR/.git" ]]; then
    err "未找到 $JARVIS_INSTALL_DIR，请先运行: sudo bash $0 install"
    exit 1
  fi
  clone_or_pull
  install_python_deps
  build_frontend
  install_systemd_unit
  start_service
  log "更新完成 ✓"
}

cmd_status() {
  systemctl status jarvis --no-pager || true
  curl -sf "http://127.0.0.1:$JARVIS_PORT/api/health" && echo || warn "健康检查失败"
}

MODE="${1:-install}"
case "$MODE" in
  install) cmd_install ;;
  update) cmd_update ;;
  status) cmd_status ;;
  -h|--help|help)
    sed -n '2,12p' "$0" | sed 's/^# \?//'
    ;;
  *)
    err "未知命令: $MODE（可用 install | update | status）"
    exit 1
    ;;
esac
