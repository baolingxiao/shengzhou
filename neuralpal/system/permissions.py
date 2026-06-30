# -*- coding: utf-8 -*-
"""系统层：macOS 权限检测与系统设置跳转。"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

PermissionKind = Literal["accessibility", "screen_recording"]


def _detect_bundle_name() -> str:
    """若从 贾维斯.app 启动，返回 App 显示名（TCC 权限列表中的名称）。"""
    if is_jarvis_app_process():
        return "贾维斯"
    try:
        exe = Path(sys.executable).resolve()
        parts = exe.parts
        for i, p in enumerate(parts):
            if p.endswith(".app") and i + 2 < len(parts) and parts[i + 1] == "Contents":
                name = p.replace(".app", "")
                return name if name else "贾维斯"
    except Exception:
        pass
    return "Python"


def _process_executable_path() -> str:
    """当前进程实际 Mach-O 路径（比 sys.executable 更可靠，alias App 下后者常指向 Python.framework）。"""
    if not _is_macos():
        return str(Path(sys.executable).resolve())
    try:
        import ctypes

        libc = ctypes.CDLL("/usr/lib/libc.dylib")
        libc.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        buf = ctypes.create_string_buffer(4096)
        if libc.proc_pidpath(os.getpid(), buf, 4096) > 0:
            return buf.value.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.debug("proc_pidpath failed: %s", exc)
    return str(Path(sys.executable).resolve())


def _app_bundle_path() -> str | None:
    raw = os.environ.get("RESOURCEPATH", "").strip()
    if raw:
        res = Path(raw).resolve()
        app_root = res.parent.parent
        if app_root.name.endswith(".app"):
            return str(app_root)
    image = _process_executable_path()
    for part in Path(image).parts:
        if part.endswith(".app"):
            idx = Path(image).parts.index(part)
            return str(Path(*Path(image).parts[: idx + 1]))
    return None


def _jarvis_app_name_from_path(path: Path | str) -> str | None:
    for part in Path(path).parts:
        if part.endswith(".app"):
            name = part.replace(".app", "")
            if name in ("贾维斯", "Jarvis"):
                return name
    return None


def is_jarvis_app_process() -> bool:
    """当前后端是否以 贾维斯.app 身份运行（TCC 应授权给 App 而非 Terminal）。"""
    bundle = _app_bundle_path()
    if bundle and _jarvis_app_name_from_path(bundle):
        return True
    if _jarvis_app_name_from_path(_process_executable_path()):
        return True
    return bool(getattr(sys, "frozen", False)) and os.environ.get("JARVIS_APP_MODE") == "1"


def _display_process_path() -> str:
    """权限面板展示用：alias App 下 proc 可能是 Python.framework，改显示 App 路径。"""
    bundle = _app_bundle_path()
    if bundle and is_jarvis_app_process():
        macos = Path(bundle) / "Contents" / "MacOS"
        for name in ("贾维斯", "Jarvis"):
            candidate = macos / name
            if candidate.is_file():
                return str(candidate)
        return str(macos)
    return _process_executable_path()


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _ax_is_process_trusted() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted  # type: ignore[import-untyped]

        return bool(AXIsProcessTrusted())
    except ImportError:
        try:
            import ctypes
            import ctypes.util

            path = ctypes.util.find_library("ApplicationServices")
            if not path:
                path = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            lib = ctypes.cdll.LoadLibrary(path)
            lib.AXIsProcessTrusted.restype = ctypes.c_bool  # type: ignore[attr-defined]
            return bool(lib.AXIsProcessTrusted())  # type: ignore[attr-defined]
        except Exception as exc:
            logger.debug("accessibility trusted check failed: %s", exc)
            return False
    except Exception as exc:
        logger.debug("accessibility trusted check failed: %s", exc)
        return False


def _accessibility_event_tap_probe() -> bool:
    """
    实时探测：能否创建 CGEventTap（Sequoia 上比 AXIsProcessTrusted 更可靠，不读缓存）。
    pyautogui 代操同样依赖此能力。
    """
    try:
        from Quartz import (  # type: ignore[import-untyped]
            CGEventTapCreate,
            CGEventTapEnable,
            kCGEventKeyDown,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            kCGSessionEventTap,
        )

        def _callback(proxy, event_type, event, refcon):  # noqa: ANN001
            return event

        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            1 << kCGEventKeyDown,
            _callback,
            None,
        )
        if tap is None:
            return False
        CGEventTapEnable(tap, False)
        return True
    except Exception as exc:
        logger.debug("accessibility event tap probe failed: %s", exc)
        return False


def _accessibility_functional_probe() -> bool:
    """尝试读取系统 AX 树；比单纯 AXIsProcessTrusted 更贴近真实代操能力。"""
    try:
        from ApplicationServices import (  # type: ignore[import-untyped]
            AXUIElementCopyAttributeValue,
            AXUIElementCreateSystemWide,
            kAXFocusedApplicationAttribute,
        )

        ref = AXUIElementCreateSystemWide()
        err, _value = AXUIElementCopyAttributeValue(ref, kAXFocusedApplicationAttribute, None)
        return int(err) == 0
    except Exception as exc:
        logger.debug("accessibility functional probe failed: %s", exc)
        return False


def check_accessibility() -> bool:
    if not _is_macos():
        return True
    if _ax_is_process_trusted():
        return True
    if _accessibility_event_tap_probe():
        return True
    return _accessibility_functional_probe()


def check_accessibility_detail() -> dict[str, bool]:
    trusted = _ax_is_process_trusted()
    event_tap = _accessibility_event_tap_probe()
    functional = _accessibility_functional_probe()
    return {
        "granted": trusted or event_tap or functional,
        "trusted_api": trusted,
        "event_tap": event_tap,
        "functional": functional,
    }


def _core_graphics():
    import ctypes

    return ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")


def _screen_recording_preflight() -> bool:
    try:
        import ctypes

        cg = _core_graphics()
        cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool  # type: ignore[attr-defined]
        return bool(cg.CGPreflightScreenCaptureAccess())  # type: ignore[attr-defined]
    except Exception as exc:
        logger.debug("screen preflight check failed: %s", exc)
        return False


def _screen_recording_screencapture_probe() -> bool:
    tmp = Path(tempfile.gettempdir()) / "neuralpal_perm_probe.png"
    try:
        tmp.unlink(missing_ok=True)
        proc = subprocess.run(
            ["screencapture", "-x", str(tmp)],
            capture_output=True,
            timeout=8,
        )
        if proc.returncode != 0 or not tmp.is_file():
            return False
        return tmp.stat().st_size > 2048
    except Exception as exc:
        logger.debug("screen screencapture probe failed: %s", exc)
        return False
    finally:
        tmp.unlink(missing_ok=True)


def check_screen_recording() -> bool:
    if not _is_macos():
        return True
    if _screen_recording_preflight():
        return True
    return _screen_recording_screencapture_probe()


def check_screen_recording_detail() -> dict[str, bool]:
    preflight = _screen_recording_preflight()
    capture = _screen_recording_screencapture_probe()
    return {
        "granted": preflight or capture,
        "preflight": preflight,
        "screencapture": capture,
    }


def _code_signing_info() -> dict[str, Any]:
    """检测是否为 adhoc/cdhash 签名（会导致系统设置开关 ON 但 AXIsProcessTrusted 仍为 false）。"""
    if not _is_macos():
        return {"stable": True, "kind": "non_macos"}
    bundle = _app_bundle_path()
    target = bundle or _process_executable_path()
    try:
        proc = subprocess.run(
            ["codesign", "-dr", "-", target],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        dr = (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:
        return {"stable": False, "kind": "unknown", "error": str(exc)}

    if "certificate leaf" in dr or "anchor apple generic" in dr:
        return {
            "stable": True,
            "kind": "certificate",
            "detail": "已用稳定证书签名，权限可跨版本保留。",
        }
    if "cdhash" in dr:
        return {
            "stable": False,
            "kind": "adhoc_cdhash",
            "detail": (
                "当前 App 为 adhoc 签名，macOS 把辅助功能绑定到二进制哈希。"
                "系统设置里开关可能仍显示 ON，但运行时检测会失败。"
                "请运行 ./scripts/macos/sign_jarvis_app.sh 后重新授权。"
            ),
            "designated_requirement": dr.strip().splitlines()[-1][:240],
        }
    return {"stable": False, "kind": "unknown", "detail": dr.strip()[:240]}


def open_system_settings(kind: PermissionKind) -> bool:
    if not _is_macos():
        return False
    urls = {
        "accessibility": (
            "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension"
            "?Privacy_Accessibility"
        ),
        "screen_recording": (
            "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension"
            "?Privacy_ScreenCapture"
        ),
    }
    legacy = {
        "accessibility": (
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        ),
        "screen_recording": (
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
        ),
    }
    for url in (urls[kind], legacy[kind]):
        try:
            subprocess.run(["open", url], check=True, timeout=5)
            return True
        except Exception:
            continue
    return False


def get_permissions_snapshot() -> dict[str, Any]:
    from neuralpal.config import get_settings

    settings = get_settings()
    allow_terminal = bool(settings.agent_allow_terminal)

    if not _is_macos():
        return {
            "platform": platform.system(),
            "agent_control_available": True,
            "running_in_app": False,
            "tcc_identity": "贾维斯",
            "accessibility": {"granted": True, "required": True},
            "screen_recording": {"granted": True, "required": True},
            "all_granted": True,
            "message": "非 macOS 环境，跳过本机权限检测。",
        }

    signing = _code_signing_info()
    acc_detail = check_accessibility_detail()
    scr_detail = check_screen_recording_detail()
    acc = acc_detail["granted"]
    scr = scr_detail["granted"]
    process_image = _display_process_path()
    bundle_path = _app_bundle_path()
    in_app = is_jarvis_app_process()
    python_name = Path(process_image).name
    tcc_name = _detect_bundle_name()
    perms_ok = acc and scr
    agent_ready = perms_ok and (in_app or allow_terminal)
    needs_app_restart = in_app and scr and not acc
    acc_detail_text = (
        f"系统 API：{'通过' if acc_detail['trusted_api'] else '未通过'}；"
        f"EventTap：{'通过' if acc_detail['event_tap'] else '未通过'}；"
        f"AX 树：{'通过' if acc_detail['functional'] else '未通过'}"
    )
    scr_detail_text = (
        f"系统 API：{'通过' if scr_detail['preflight'] else '未通过'}；"
        f"截图探测：{'通过' if scr_detail['screencapture'] else '未通过'}"
    )
    return {
        "platform": "Darwin",
        "agent_control_available": agent_ready,
        "running_in_app": in_app,
        "allow_terminal_agent": allow_terminal,
        "tcc_identity": tcc_name,
        "backend_process_path": process_image,
        "backend_process_name": python_name,
        "app_bundle_path": bundle_path,
        "bundle_name": tcc_name,
        "accessibility": {
            "granted": acc,
            "required": True,
            "label": "辅助功能",
            "detail": (
                f"请在「系统设置 → 隐私与安全性 → 辅助功能」中打开「{tcc_name}」。"
                f"（与屏幕录制是不同页面）"
                if in_app
                else "请改用 dist/贾维斯.app 启动；Terminal/Python 授权无法用于代操。"
            ),
            "probe": acc_detail_text,
        },
        "screen_recording": {
            "granted": scr,
            "required": True,
            "label": "屏幕录制",
            "detail": (
                f"请在「系统设置 → 隐私与安全性 → 录屏与系统录音」中打开「{tcc_name}」。"
                if in_app
                else "请改用 dist/贾维斯.app 启动。"
            ),
            "probe": scr_detail_text,
        },
        "all_granted": agent_ready,
        "system_permissions_granted": perms_ok,
        "needs_app_restart": needs_app_restart,
        "code_signing": signing,
        "tcc_cdhash_mismatch_suspected": (
            in_app
            and not signing.get("stable", True)
            and not acc
            and signing.get("kind") == "adhoc_cdhash"
        ),
        "message": (
            "本机/网页代操已就绪。"
            if agent_ready
            else (
                signing.get("detail")
                if signing.get("kind") == "adhoc_cdhash" and in_app and not acc
                else (
                    "辅助功能与屏幕录制是两项独立权限。"
                    "若辅助功能列表里已打开「贾维斯」仍显示未授权：先关闭再打开该开关，然后按 ⌘Q 完全退出后重开。"
                    "重新打包 App 后也可能需要重新授权。"
                    if needs_app_restart or (in_app and not acc)
                    else (
                        f"请为「{tcc_name}」分别开启辅助功能与屏幕录制；点「一键授权」按系统提示操作。"
                        if in_app
                        else (
                            "当前从 Terminal/Python 启动，系统设置里只会出现 Terminal 或 Python，无法以「贾维斯」授权。"
                            "请运行 ./scripts/macos/make_jarvis_app.sh 构建后，双击 dist/贾维斯.app 启动。"
                            + (
                                "（开发者可在 .env 设置 NEURALPAL_ALLOW_TERMINAL_AGENT=true 临时跳过）"
                                if not allow_terminal
                                else ""
                            )
                        )
                    )
                )
            )
        ),
    }


def auto_setup_permissions() -> dict[str, Any]:
    from neuralpal.config import get_settings

    snap = get_permissions_snapshot()
    if _is_macos() and not is_jarvis_app_process() and not get_settings().agent_allow_terminal:
        return {
            "all_granted": False,
            "message": snap.get("message") or "请使用 贾维斯.app 启动后再授权。",
            "steps": [],
            "snapshot": snap,
        }

    from neuralpal.system.permissions_mac import run_auto_permission_setup

    result = run_auto_permission_setup()
    snap = get_permissions_snapshot()
    result.update(
        {
            "snapshot": snap,
            "all_granted": snap.get("all_granted", False),
        }
    )
    return result
