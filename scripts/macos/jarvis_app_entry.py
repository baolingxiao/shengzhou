#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贾维斯 macOS App 入口。

必须从 贾维斯.app 启动，系统「辅助功能 / 屏幕录制」才会显示并授权给「贾维斯」，
而不是 Terminal / Python。

开发调试仍可用 ./scripts/run_jarvis.sh（会显示 Python，仅开发者使用）。
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _prefer_venv_site_packages(root: Path) -> None:
    """alias 模式避免混用系统 Framework 与 .venv 的 site-packages（如 numpy 版本冲突）。"""
    venv_lib = root / ".venv" / "lib"
    for site in venv_lib.glob("python*/site-packages"):
        site_s = str(site.resolve())
        sys.path = [
            p
            for p in sys.path
            if not (p.endswith("site-packages") and "/Python.framework/" in p)
        ]
        if site_s not in sys.path:
            sys.path.insert(0, site_s)
        break


def _ensure_project_root() -> Path:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        resources = exe.parent.parent / "Resources"
        candidates.extend([resources / "project", resources])
    candidates.append(Path(__file__).resolve().parents[2])

    for raw in candidates:
        root = raw.resolve()
        if (root / "neuralpal").exists() and (root / "server").exists():
            root_s = str(root)
            if root_s not in sys.path:
                sys.path.insert(0, root_s)
            _prefer_venv_site_packages(root)
            os.chdir(root)
            return root

    raise RuntimeError(
        "找不到贾维斯项目文件。请重新运行 ./scripts/macos/make_jarvis_app.sh 构建 App。"
    )


ROOT = _ensure_project_root()

os.environ.setdefault("NEURALPAL_BACKEND_PORT", "8766")


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        example = ROOT / ".env.example"
        if example.is_file():
            import shutil

            shutil.copy(example, env_path)
            print("[贾维斯] 已从 .env.example 创建 .env，请填写 API 密钥后重启 App。")
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        pass


def _request_permissions_once() -> None:
    """启动时仅被动检测，不自动唤起 macOS 系统授权弹窗。"""
    try:
        from neuralpal.system.permissions import get_permissions_snapshot

        snap = get_permissions_snapshot()
        if snap.get("all_granted"):
            return
        if snap.get("needs_app_restart"):
            print("[贾维斯] 系统设置已授权辅助功能后，请 ⌘Q 完全退出再重新打开。")
            return
        if snap.get("system_permissions_granted"):
            print("[贾维斯] 系统权限已就绪。")
            return
        print("[贾维斯] 首次使用请在应用内左下角「权限」完成授权。")
    except Exception as exc:
        print(f"[贾维斯] 权限检查跳过：{exc}")


def _backend_alive(port: int) -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=1
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


def _port_in_use(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _pids_on_port(port: int) -> list[int]:
    import subprocess

    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    pids: list[int] = []
    for line in out.strip().splitlines():
        try:
            pids.append(int(line.strip()))
        except ValueError:
            continue
    return pids


def _kill_pids(pids: list[int]) -> None:
    import signal

    for pid in pids:
        if pid <= 1 or pid == os.getpid():
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def _clear_stale_port(port: int) -> bool:
    """端口被占但 /api/health 失败时，尝试结束僵尸进程。"""
    if not _port_in_use(port) or _backend_alive(port):
        return True
    stale = _pids_on_port(port)
    if not stale:
        return False
    print(f"[贾维斯] 端口 {port} 被无响应进程占用，正在清理：{stale}")
    _kill_pids(stale)
    for _ in range(20):
        if not _port_in_use(port):
            return True
        time.sleep(0.15)
    return not _port_in_use(port)


def _alert(title: str, message: str) -> None:
    """macOS 弹窗（双击 App 时 print 用户看不到）。"""
    print(f"[贾维斯] {title}: {message}")
    try:
        import subprocess

        script = f'display alert "{title}" message "{message}" as critical'
        subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except Exception:
        pass


def _open_browser(port: int) -> None:
    url = f"http://127.0.0.1:{port}/"
    for _ in range(30):
        if _backend_alive(port):
            webbrowser.open(url)
            print(f"[贾维斯] 已打开 {url}")
            return
        time.sleep(0.3)
    webbrowser.open(url)


def _backend_running_in_app(port: int) -> bool | None:
    """True=App 进程, False=Terminal/Python, None=无法探测。"""
    try:
        import json
        import urllib.request

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/system/permissions", timeout=2
        ) as resp:
            data = json.loads(resp.read())
            return bool(data.get("running_in_app"))
    except Exception:
        return None


def _replace_dev_backend(port: int) -> bool:
    """App 启动时清掉占用端口的 Terminal/Python 调试后端。"""
    stale = _pids_on_port(port)
    if not stale:
        return False
    print(f"[贾维斯] 端口 {port} 被开发模式占用，正在切换为 App 进程：{stale}")
    _kill_pids(stale)
    for _ in range(40):
        if not _port_in_use(port):
            return True
        time.sleep(0.15)
    return not _port_in_use(port)


def main() -> None:
    from neuralpal.system.permissions import is_jarvis_app_process

    from_app = is_jarvis_app_process()
    if from_app:
        os.environ["JARVIS_APP_MODE"] = "1"

    _load_dotenv()
    _request_permissions_once()

    port = int(os.environ.get("NEURALPAL_BACKEND_PORT", "8766"))

    if _backend_alive(port):
        in_app = _backend_running_in_app(port)
        if from_app and in_app is False:
            if _replace_dev_backend(port):
                pass  # 继续在本进程启动 App 后端
            else:
                _alert(
                    "贾维斯无法启动",
                    f"端口 {port} 被开发模式占用且无法自动清理。"
                    "请在活动监视器结束 Python 进程后重试。",
                )
                return
        else:
            print(f"[贾维斯] 服务已在运行，直接打开浏览器 127.0.0.1:{port}")
            _open_browser(port)
            return

    if _port_in_use(port):
        if _clear_stale_port(port) and _backend_alive(port):
            print(f"[贾维斯] 已恢复旧服务，打开浏览器 127.0.0.1:{port}")
            _open_browser(port)
            return
        if _clear_stale_port(port):
            pass  # 端口已释放，继续正常启动
        else:
            msg = (
                f"端口 {port} 被其他程序占用且无法自动清理。"
                "请在「活动监视器」搜索「贾维斯」或「Python」并结束进程后重试。"
            )
            _alert("贾维斯无法启动", msg)
            return

    mode_label = "App 模式 · 权限主体=贾维斯" if from_app else "开发模式 · Terminal/Python"
    print(f"[贾维斯] 启动服务 127.0.0.1:{port} （{mode_label}）")

    threading.Timer(1.5, lambda: _open_browser(port)).start()

    import uvicorn

    uvicorn.run(
        "server.main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
