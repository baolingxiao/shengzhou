# -*- coding: utf-8 -*-
"""macOS 屏幕截图与键鼠控制（Computer Use 执行层）。"""

from __future__ import annotations

import base64
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCREENSHOT_PATH = Path(tempfile.gettempdir()) / "neuralpal_screen.png"


def get_display_size() -> tuple[int, int]:
    try:
        import pyautogui  # type: ignore[import-untyped]

        w, h = pyautogui.size()
        return int(w), int(h)
    except Exception:
        return 1440, 900


def take_screenshot_b64() -> tuple[str, str]:
    """截屏并压缩，返回 (base64, media_type)。"""
    _SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["screencapture", "-x", str(_SCREENSHOT_PATH)],
            check=True,
            capture_output=True,
            timeout=15,
        )
        logical_w, logical_h = get_display_size()
        try:
            from PIL import Image

            with Image.open(_SCREENSHOT_PATH) as img:
                if img.size != (logical_w, logical_h):
                    img = img.resize((logical_w, logical_h), Image.Resampling.LANCZOS)
                import io

                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=72, optimize=True)
                raw = buf.getvalue()
        except ImportError:
            raw = _SCREENSHOT_PATH.read_bytes()
            return base64.standard_b64encode(raw).decode("ascii"), "image/png"

        return base64.standard_b64encode(raw).decode("ascii"), "image/jpeg"
    except Exception as exc:
        logger.exception("screenshot failed")
        raise RuntimeError(f"截图失败：{exc}") from exc


def _screenshot_image_block(b64: str, *, media_type: str = "image/jpeg") -> dict[str, Any]:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": b64},
    }


def _paste_text(text: str) -> None:
    """通过剪贴板输入（支持中文）。"""
    import pyautogui  # type: ignore[import-untyped]

    try:
        import pyperclip  # type: ignore[import-untyped]

        pyperclip.copy(text)
        pyautogui.hotkey("command", "v")
        time.sleep(0.15)
        return
    except Exception:
        pass
    pyautogui.write(text, interval=0.02)


def execute_computer_action(action_input: dict[str, Any]) -> dict[str, Any]:
    """
    执行 Anthropic computer tool 的单步动作，返回 tool_result 内容块列表。
    """
    import pyautogui  # type: ignore[import-untyped]

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.08

    action = str(action_input.get("action") or "")
    if action == "screenshot":
        b64, media = take_screenshot_b64()
        return {
            "type": "tool_result",
            "content": [_screenshot_image_block(b64, media_type=media)],
        }

    if action == "mouse_move":
        coord = action_input.get("coordinate") or [0, 0]
        pyautogui.moveTo(int(coord[0]), int(coord[1]), duration=0.12)
    elif action == "left_click":
        coord = action_input.get("coordinate")
        if coord:
            pyautogui.click(int(coord[0]), int(coord[1]))
        else:
            pyautogui.click()
    elif action == "double_click":
        coord = action_input.get("coordinate")
        if coord:
            pyautogui.doubleClick(int(coord[0]), int(coord[1]))
        else:
            pyautogui.doubleClick()
    elif action == "right_click":
        coord = action_input.get("coordinate")
        if coord:
            pyautogui.rightClick(int(coord[0]), int(coord[1]))
        else:
            pyautogui.rightClick()
    elif action == "type":
        _paste_text(str(action_input.get("text") or ""))
    elif action == "key":
        key_text = str(action_input.get("text") or "")
        keys = key_text.split("+")
        if len(keys) > 1:
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key_text)
    elif action == "scroll":
        amount = int(action_input.get("scroll_amount") or 3)
        direction = str(action_input.get("scroll_direction") or "down")
        clicks = amount if direction == "down" else -amount
        coord = action_input.get("coordinate")
        if coord:
            pyautogui.scroll(clicks, int(coord[0]), int(coord[1]))
        else:
            pyautogui.scroll(clicks)
    elif action == "wait":
        time.sleep(min(float(action_input.get("duration") or 1.0), 10.0))
    elif action == "left_click_drag":
        start = action_input.get("start_coordinate") or [0, 0]
        end = action_input.get("coordinate") or start
        pyautogui.moveTo(int(start[0]), int(start[1]))
        pyautogui.dragTo(int(end[0]), int(end[1]), duration=0.35, button="left")
    else:
        return {"type": "tool_result", "content": f"[未知动作] {action}"}

    b64, media = take_screenshot_b64()
    return {
        "type": "tool_result",
        "content": [
            {"type": "text", "text": f"executed: {action}"},
            _screenshot_image_block(b64, media_type=media),
        ],
    }


def mock_execute(goal: str) -> str:
    return f"[模拟执行完成] 目标：{goal}（NEURALPAL_AGENT_MOCK_MODE=true，未实际操作键鼠）"
