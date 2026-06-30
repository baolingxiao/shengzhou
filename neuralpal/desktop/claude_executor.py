# -*- coding: utf-8 -*-
"""Claude Computer Use 执行循环。"""

from __future__ import annotations

import logging
from typing import Any

from neuralpal.config import get_settings
from neuralpal.desktop.mac_control import execute_computer_action, get_display_size, mock_execute
from neuralpal.llm.claude_client import get_anthropic_client

logger = logging.getLogger(__name__)

# 最近一次 Computer Use 循环中执行的非 screenshot 动作次数（供完成判定）
LAST_ACTION_COUNT = 0

_BETA_CANDIDATES = (
    ["computer-use-2025-11-24"],
    ["computer-use-2025-01-24"],
    ["computer-use-2024-10-22"],
)
_TOOL_CANDIDATES = (
    "computer_20251124",
    "computer_20250124",
    "computer_20241022",
)


def _resolve_computer_use(model: str) -> list[tuple[list[str], str]]:
    """按模型选择 Computer Use 的 beta / tool 组合（Sonnet 4.6 需 20251124）。"""
    m = (model or "").lower()
    if any(x in m for x in ("sonnet-4-6", "opus-4-6", "opus-4-7", "opus-4-8", "opus-4-5")):
        return [
            (["computer-use-2025-11-24"], "computer_20251124"),
            (["computer-use-2025-01-24"], "computer_20250124"),
        ]
    if any(x in m for x in ("4-5", "4.5", "haiku-4")):
        return [
            (["computer-use-2025-01-24"], "computer_20250124"),
            (["computer-use-2024-10-22"], "computer_20241022"),
        ]
    pairs: list[tuple[list[str], str]] = []
    for beta in _BETA_CANDIDATES:
        for tool in _TOOL_CANDIDATES:
            pairs.append((list(beta), tool))
    return pairs


def _finalize_computer_use_result(last_text: str, goal: str) -> str:
    from neuralpal.desktop.computer_use_helpers import computer_use_completed

    text = (last_text or "").strip()
    if computer_use_completed(text, goal=goal, actions_taken=LAST_ACTION_COUNT):
        return text or "已完成。"
    snippet = text[:600] if text else "（模型未返回说明）"
    return (
        f"【执行未完成】未达成目标（已操作 {LAST_ACTION_COUNT} 步）。"
        f"请确认微信窗口在前台，而非贾维斯浏览器页面。\n"
        f"停步说明：{snippet}"
    )


def _strip_images_from_tool_results(messages: list[dict[str, Any]], *, keep_last: int = 1) -> None:
    """只保留最近 keep_last 条含截图的 tool_result，其余去掉 image 块。"""
    image_tool_indices: list[tuple[int, int]] = []

    for mi, msg in enumerate(messages):
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for bi, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            inner = block.get("content")
            if isinstance(inner, list) and any(
                isinstance(x, dict) and x.get("type") == "image" for x in inner
            ):
                image_tool_indices.append((mi, bi))

    for mi, bi in image_tool_indices[:-keep_last]:
        block = messages[mi]["content"][bi]
        inner = block.get("content")
        if not isinstance(inner, list):
            continue
        block["content"] = [
            x for x in inner if not (isinstance(x, dict) and x.get("type") == "image")
        ]
        if not block["content"]:
            block["content"] = [{"type": "text", "text": "[screenshot omitted]"}]


def run_claude_computer_task(goal: str, *, mock: bool = False) -> str:
    global LAST_ACTION_COUNT
    LAST_ACTION_COUNT = 0
    s = get_settings()
    if mock or s.agent_mock_mode:
        return mock_execute(goal)
    if not (s.anthropic_api_key or "").strip():
        return "【执行失败】未配置 ANTHROPIC_API_KEY，无法使用 Claude Computer Use。"

    width, height = get_display_size()
    client = get_anthropic_client()
    model = s.agent_claude_model or s.anthropic_model_sonnet
    max_steps = s.agent_max_steps
    messages: list[dict[str, Any]] = [{"role": "user", "content": goal}]
    last_text = ""

    for step in range(max_steps):
        response = None
        last_err: Exception | None = None
        for betas, tool_type in _resolve_computer_use(model):
            try:
                _strip_images_from_tool_results(messages)
                response = client.beta.messages.create(
                    model=model,
                    max_tokens=s.agent_claude_max_tokens,
                    betas=betas,
                    tools=[
                        {
                            "type": tool_type,
                            "name": "computer",
                            "display_width_px": width,
                            "display_height_px": height,
                            "display_number": 1,
                        }
                    ],
                    messages=messages,
                )
                break
            except Exception as exc:
                last_err = exc
                response = None
        if response is None:
            raise RuntimeError(f"Claude Computer Use 调用失败：{last_err}")

        text_parts: list[str] = []
        tool_uses: list[Any] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", "") or "")
            elif getattr(block, "type", None) == "tool_use":
                tool_uses.append(block)
        if text_parts:
            last_text = "\n".join(text_parts).strip()

        if response.stop_reason == "end_turn" and not tool_uses:
            return _finalize_computer_use_result(last_text, goal)

        if not tool_uses:
            return _finalize_computer_use_result(last_text, goal)

        messages.append({"role": "assistant", "content": response.content})
        tool_results: list[dict[str, Any]] = []
        for tu in tool_uses:
            name = getattr(tu, "name", "")
            tu_id = getattr(tu, "id", "")
            inp = getattr(tu, "input", {}) or {}
            if name != "computer":
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": f"[跳过] 不支持的工具：{name}",
                    }
                )
                continue
            try:
                action_name = str((inp if isinstance(inp, dict) else {}).get("action") or "")
                if action_name and action_name != "screenshot":
                    LAST_ACTION_COUNT += 1
                result = execute_computer_action(inp if isinstance(inp, dict) else {})
                content = result.get("content")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": content,
                    }
                )
            except Exception as exc:
                logger.exception("computer action failed")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": f"[执行错误] {exc}",
                        "is_error": True,
                    }
                )
        messages.append({"role": "user", "content": tool_results})
        _strip_images_from_tool_results(messages)

    exhausted = last_text or f"已达最大步数（{max_steps}），请检查屏幕状态或继续指示。"
    return _finalize_computer_use_result(exhausted, goal)
