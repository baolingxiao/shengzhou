#!/usr/bin/env bash
# 用稳定的自签名证书签署 贾维斯.app，避免 macOS TCC 把辅助功能绑到每次构建都变的 cdhash。
# 参考：https://www.nick-liu.com/posts/tcc-cdhash-trap/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CERT_NAME="${JARVIS_CODESIGN_IDENTITY:-Jarvis Code Signing}"
APP="${1:-/Applications/贾维斯.app}"

log() { printf '\033[1;36m[jarvis-sign]\033[0m %s\n' "$*" >&2; }
err() { printf '\033[1;31m[jarvis-sign]\033[0m %s\n' "$*" >&2; }

if [[ "$(uname -s)" != "Darwin" ]]; then
  err "仅支持 macOS"
  exit 1
fi

if [[ ! -d "$APP" ]]; then
  APP="$ROOT/dist/贾维斯.app"
fi
if [[ ! -d "$APP" ]]; then
  err "未找到 App：$APP"
  err "请先运行 ./scripts/macos/make_jarvis_app.sh"
  exit 1
fi

find_identity() {
  if [[ -n "${JARVIS_CODESIGN_IDENTITY:-}" ]]; then
    printf '%s' "$JARVIS_CODESIGN_IDENTITY"
    return
  fi
  security find-identity -v -p codesigning 2>/dev/null \
    | grep "Apple Development:" \
    | head -1 \
    | sed -n 's/.*"\(.*\)".*/\1/p'
}

ensure_cert() {
  local id
  id="$(find_identity || true)"
  if [[ -n "$id" ]]; then
    log "使用签名身份：$id"
    printf '%s' "$id"
    return
  fi

  log "创建自签名代码签名证书「$CERT_NAME」…"
  local tmp
  tmp="$(mktemp -d)"
  local cleanup_tmp=1
  cleanup() { [[ "$cleanup_tmp" == 1 ]] && rm -rf "$tmp"; }
  trap cleanup EXIT

  openssl req -x509 -newkey rsa:2048 \
    -keyout "$tmp/key.pem" -out "$tmp/cert.pem" \
    -days 825 -nodes \
    -subj "/CN=$CERT_NAME/O=NeuralPal/C=CN" 2>/dev/null

  openssl pkcs12 -export \
    -out "$tmp/cert.p12" \
    -inkey "$tmp/key.pem" \
    -in "$tmp/cert.pem" \
    -passout pass: 2>/dev/null

  security import "$tmp/cert.p12" -k ~/Library/Keychains/login.keychain-db \
    -P "" -T /usr/bin/codesign -T /usr/bin/security 2>/dev/null \
    || security import "$tmp/cert.p12" -k ~/Library/Keychains/login.keychain \
    -P "" -T /usr/bin/codesign -T /usr/bin/security 2>/dev/null \
    || true

  security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "" \
    ~/Library/Keychains/login.keychain-db 2>/dev/null \
    || security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "" \
    ~/Library/Keychains/login.keychain 2>/dev/null \
    || true

  id="$(find_identity || true)"
  if [[ -z "$id" ]]; then
    err "证书创建失败。请打开「钥匙串访问」手动创建「代码签名」证书后重试。"
    exit 1
  fi
  log "证书已就绪：$id"
  printf '%s' "$id"
}

sign_app() {
  local identity="$1"
  local exe="$APP/Contents/MacOS/贾维斯"
  local ent="$ROOT/scripts/macos/jarvis_entitlements.plist"
  log "签署 $exe …"
  # alias 模式 App 含大量 symlink，--deep 会失败；TCC 校验的是主 Mach-O 进程。
  local sign_args=(--force --sign "$identity" --identifier com.neuralpal.jarvis --timestamp=none)
  if [[ -f "$ent" ]]; then
    sign_args+=(--entitlements "$ent")
  fi
  codesign "${sign_args[@]}" "$exe"
  codesign --verify --strict "$exe"
  # bundle 外壳：不 deep，避免 symlink 失败；不用 entitlements 避免二次签名冲突
  codesign --force --sign "$identity" --identifier com.neuralpal.jarvis --timestamp=none "$APP" 2>/dev/null \
    || log "bundle 外壳签署跳过（executable 已签署，通常足够）"
  log "签署完成。Designated Requirement："
  codesign -dr - "$exe" 2>&1 | sed 's/^/  /' >&2
}

reset_tcc_if_requested() {
  if [[ "${JARVIS_RESET_TCC:-0}" == "1" ]]; then
    log "重置 TCC 记录（需重新在系统设置里打开开关）…"
    tccutil reset Accessibility com.neuralpal.jarvis 2>/dev/null || true
    tccutil reset ScreenCapture com.neuralpal.jarvis 2>/dev/null || true
    tccutil reset ListenEvent com.neuralpal.jarvis 2>/dev/null || true
  fi
}

main() {
  local identity
  identity="$(ensure_cert)"
  sign_app "$identity"
  reset_tcc_if_requested
  log ""
  log "【重要】若辅助功能开关已开但仍检测失败："
  log "  1. 运行：JARVIS_RESET_TCC=1 $0"
  log "  2. 系统设置 → 辅助功能 / 录屏 → 重新打开「贾维斯」"
  log "  3. ⌘Q 完全退出贾维斯后重新打开"
}

main
