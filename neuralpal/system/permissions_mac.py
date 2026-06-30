# -*- coding: utf-8 -*-
"""macOS 交互式权限请求（唤起系统弹窗，无需用户手动 + 添加 Python）。"""

from __future__ import annotations

import ctypes
import logging
import platform
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def request_accessibility_interactive() -> dict[str, Any]:
    """
    唤起 macOS 辅助功能授权流程。
    通常会弹出系统对话框或跳转系统设置，用户点「打开系统设置」并勾选即可。
    """
    if not _is_macos():
        return {"ok": True, "granted": True, "method": "skip_non_macos"}

    from neuralpal.system.permissions import check_accessibility

    if check_accessibility():
        return {"ok": True, "granted": True, "method": "already_granted"}
    try:
        from ApplicationServices import (  # type: ignore[import-untyped]
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )

        options = {kAXTrustedCheckOptionPrompt: True}
        granted = bool(AXIsProcessTrustedWithOptions(options))
        return {
            "ok": True,
            "granted": granted,
            "method": "system_prompt",
            "user_action": "若弹出对话框，请点「打开系统设置」并打开「贾维斯」开关。",
        }
    except ImportError:
        logger.warning("ApplicationServices unavailable; fallback open settings")
    except Exception as exc:
        logger.exception("accessibility interactive request failed")
        return {"ok": False, "granted": False, "method": "error", "error": str(exc)}

    try:
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension"
                "?Privacy_Accessibility",
            ],
            check=False,
            timeout=5,
        )
        return {
            "ok": True,
            "granted": False,
            "method": "open_settings",
            "user_action": "请在辅助功能列表中打开「贾维斯」。",
        }
    except Exception as exc:
        return {"ok": False, "granted": False, "method": "error", "error": str(exc)}


def request_screen_recording_interactive() -> dict[str, Any]:
    """唤起 macOS 屏幕录制授权对话框（10.15+）。"""
    if not _is_macos():
        return {"ok": True, "granted": True, "method": "skip_non_macos"}

    from neuralpal.system.permissions import check_screen_recording

    if check_screen_recording():
        return {"ok": True, "granted": True, "method": "already_granted"}

    try:
        import ctypes

        cg = ctypes.CDLL(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
        )
        cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool  # type: ignore[attr-defined]
        if bool(cg.CGPreflightScreenCaptureAccess()):  # type: ignore[attr-defined]
            return {"ok": True, "granted": True, "method": "preflight_granted"}
        cg.CGRequestScreenCaptureAccess.restype = ctypes.c_bool  # type: ignore[attr-defined]
        granted = bool(cg.CGRequestScreenCaptureAccess())  # type: ignore[attr-defined]
        return {
            "ok": True,
            "granted": granted,
            "method": "system_dialog",
            "user_action": (
                "若弹出「录屏」提示，请允许；否则在系统设置 → 屏幕录制中打开开关。"
            ),
        }
    except Exception as exc:
        logger.exception("screen recording interactive request failed")
        try:
            subprocess.run(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension"
                    "?Privacy_ScreenCapture",
                ],
                check=False,
                timeout=5,
            )
            return {
                "ok": True,
                "granted": False,
                "method": "open_settings",
                "user_action": "请在屏幕录制中打开贾维斯或 Python。",
            }
        except Exception as exc2:
            return {"ok": False, "granted": False, "method": "error", "error": str(exc2)}


def run_auto_permission_setup() -> dict[str, Any]:
    """
    按顺序唤起系统授权 UI，供前端「一键授权」调用。
    无法绕过用户点击（Apple 安全策略），但无需手动浏览路径。
    """
    from neuralpal.system.permissions import check_accessibility, check_screen_recording

    steps: list[dict[str, Any]] = []

    if not check_accessibility():
        steps.append({"kind": "accessibility", **request_accessibility_interactive()})
    else:
        steps.append({"kind": "accessibility", "ok": True, "granted": True, "method": "already_granted"})

    if not check_screen_recording():
        steps.append({"kind": "screen_recording", **request_screen_recording_interactive()})
    else:
        steps.append(
            {"kind": "screen_recording", "ok": True, "granted": True, "method": "already_granted"}
        )

    return {
        "steps": steps,
        "accessibility_granted": check_accessibility(),
        "screen_recording_granted": check_screen_recording(),
        "all_granted": check_accessibility() and check_screen_recording(),
        "message": (
            "系统授权窗口已唤起，请按提示点击「允许」或打开开关；贾维斯会自动检测完成。"
            if not (check_accessibility() and check_screen_recording())
            else "权限已就绪。"
        ),
    }
